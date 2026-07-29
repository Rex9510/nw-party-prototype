"""/api/v1/activities 培训活动路由。"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.activity import (
    Activity,
    ActivityAttachment,
    ActivityParticipant,
)
from app.models.audit import AuditFlow, AuditLog
from app.models.party import Branch, Community
from app.models.member import Member
from app.models.user import User
from app.schemas.activity import (
    ActivityCreate,
    ActivityListItem,
    ActivityListResponse,
    ActivityOut,
    ActivityUpdate,
    AttachmentOut,
    ParticipantIn,
    validate_organize_and_methods,
)


class AttachmentCreate(BaseModel):
    kind: str = "photo"  # photo / signin
    file_url: str
    file_size: int | None = None
    sort: int = 0
from app.services.permissions import get_member_scope_filter

router = APIRouter(prefix="/activities", tags=["activities"])


def _can_manage_activities(user: User) -> bool:
    return user.role in (User.ROLE_ADMIN, User.ROLE_STREET_LEAD, User.ROLE_COMMUNITY_ORG, User.ROLE_BRANCH_SEC)


@router.get("", response_model=ActivityListResponse)
async def list_activities(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: str | None = Query(None, alias="status"),
    community_id: int | None = None,
    branch_id: int | None = None,
    keyword: str | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ActivityListResponse:
    """活动列表。"""
    stmt = select(Activity).order_by(Activity.training_at.desc(), Activity.id.desc())

    # 角色数据范围
    scope = get_member_scope_filter(user)
    if "community_id" in scope and scope["community_id"]:
        stmt = stmt.where(Activity.community_id == scope["community_id"])
        if branch_id:
            stmt = stmt.where(Activity.organizer_branch_id == branch_id)
    elif "branch_id" in scope and scope["branch_id"]:
        stmt = stmt.where(Activity.organizer_branch_id == scope["branch_id"])
    elif "street_id" in scope and scope["street_id"]:
        stmt = stmt.join(Community, Activity.community_id == Community.id).where(
            Community.street_id == scope["street_id"]
        )
        if community_id:
            stmt = stmt.where(Activity.community_id == community_id)
        if branch_id:
            stmt = stmt.where(Activity.organizer_branch_id == branch_id)

    if status_filter:
        stmt = stmt.where(Activity.status == status_filter)

    if keyword:
        like = f"%{keyword}%"
        stmt = stmt.where(or_(Activity.theme.like(like), Activity.location.like(like)))

    # 总数
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar() or 0

    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(stmt)
    activities = result.scalars().all()

    return ActivityListResponse(
        total=total,
        items=[ActivityListItem.model_validate(a) for a in activities],
    )


@router.get("/{activity_id}", response_model=ActivityOut)
async def get_activity(
    activity_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ActivityOut:
    r = await db.execute(
        select(Activity)
        .options(
            selectinload(Activity.participants),
            selectinload(Activity.attachments),
        )
        .where(Activity.id == activity_id)
    )
    a = r.scalar_one_or_none()
    if not a:
        raise HTTPException(status_code=404, detail="活动不存在")

    # 权限校验（v2026-07-28：社区组织员 = 本社区权限；普通党员 = 本支部）
    if user.role in (User.ROLE_COMMUNITY_ORG, User.ROLE_BRANCH_SEC) and a.community_id != user.community_id:
        raise HTTPException(status_code=403, detail="无权查看")
    if user.role == User.ROLE_MEMBER:
        # v3: organizer_branch_id 可能为 None（上级送课），用 co_organize_branch_ids 判断
        allowed_branches = set(a.co_organize_branch_ids or [])
        if user.branch_id not in allowed_branches:
            raise HTTPException(status_code=403, detail="无权查看")

    # 查参与党员的名字/电话/所属组织
    member_ids = [p.member_id for p in a.participants]
    member_map: dict[int, Member] = {}
    if member_ids:
        from app.models.party import Branch as _Branch
        mr = await db.execute(
            select(Member)
            .options(selectinload(Member.branch).selectinload(_Branch.community))
            .where(Member.id.in_(member_ids))
        )
        for m in mr.scalars().all():
            member_map[m.id] = m

    from app.schemas.activity import ParticipantOut
    out = ActivityOut.model_validate(a)
    out.participants = [
        ParticipantOut(
            id=p.id,
            member_id=p.member_id,
            study_hours=p.study_hours,
            attendance_status=p.attendance_status,
            member_name=member_map[p.member_id].name if p.member_id in member_map else None,
            member_phone=member_map[p.member_id].phone if p.member_id in member_map else None,
            member_org_level=member_map[p.member_id].org_level if p.member_id in member_map else None,
            member_branch_name=member_map[p.member_id].branch.name
                if p.member_id in member_map and member_map[p.member_id].branch else None,
        )
        for p in a.participants
    ]
    # 社区/街道名二次查（不在 Member 上，需要走 community_map + street_map）
    if member_ids:
        cids = {m.community_id for m in member_map.values() if m.community_id}
        sids = {m.street_id for m in member_map.values() if m.street_id}
        from app.models.party import Community as _Community, Street as _Street
        cmap: dict[int, str] = {}
        smap: dict[int, str] = {}
        if cids:
            cr = await db.execute(select(_Community.id, _Community.name).where(_Community.id.in_(cids)))
            cmap = {r[0]: r[1] for r in cr.all()}
        if sids:
            sr = await db.execute(select(_Street.id, _Street.name).where(_Street.id.in_(sids)))
            smap = {r[0]: r[1] for r in sr.all()}
        for p in out.participants:
            m = member_map.get(p.member_id)
            if m:
                p.member_community_name = cmap.get(m.community_id) if m.community_id else None
                p.member_street_name = smap.get(m.street_id) if m.street_id else None
    return out


@router.post("", response_model=ActivityOut, status_code=201)
async def create_activity(
    body: ActivityCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ActivityOut:
    """录入培训活动（草稿状态）。"""
    if not _can_manage_activities(user):
        raise HTTPException(status_code=403, detail="无权录入活动")

    # v3 业务校验（手调，不放 schema model_validator，避免详情接口对老数据 422）
    try:
        validate_organize_and_methods(body.model_dump())
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    # v3: 举办方式改为 organize_type + co_organize_branch_ids（自行组织时填） / upper_org（上级送课时填）。
    # community_id 仍然必填冗余，从 co_organize_branch_ids[0] 反查得到。
    # organizer_branch_id 仅做审计占位（取 co_organize_branch_ids[0]）。
    community_id: int | None = None
    organizer_branch_id: int | None = None

    if body.organize_type == "self_organize":
        # 校验协办支部：全部存在 + 同一社区
        if not body.co_organize_branch_ids:
            raise HTTPException(status_code=400, detail="自行组织必须选择至少 1 个协办支部")
        brs_r = await db.execute(
            select(Branch).where(Branch.id.in_(body.co_organize_branch_ids))
        )
        branches = brs_r.scalars().all()
        if len(branches) != len(set(body.co_organize_branch_ids)):
            raise HTTPException(status_code=400, detail="部分协办支部不存在")
        community_ids = {b.community_id for b in branches}
        if len(community_ids) != 1:
            raise HTTPException(status_code=400, detail="所有协办支部必须在同一社区")
        community_id = community_ids.pop()
        # 兼容老字段：organizer_branch_id 记第一个
        organizer_branch_id = body.co_organize_branch_ids[0]
        # 角色权限校验（只校验社区级，街道级全看）
        if user.role in (User.ROLE_COMMUNITY_ORG, User.ROLE_BRANCH_SEC) and user.community_id != community_id:
            raise HTTPException(status_code=403, detail="无权在该社区录入")
        # v2026-07-28：社区组织员可在本社区下任何支部录入活动
    else:  # upper_send
        if not body.upper_org or not body.upper_org.strip():
            raise HTTPException(status_code=400, detail="上级送课必须填写具体部门")
        # 上级送课：community_id 从创建者上下文推（默认放创建者所在社区，否则取第一社区）
        if user.community_id:
            community_id = user.community_id
        else:
            # 兜底：取第一社区
            r = await db.execute(select(Community).order_by(Community.id).limit(1))
            c = r.scalar_one_or_none()
            community_id = c.id if c else 1
        organizer_branch_id = None

    if community_id is None:
        raise HTTPException(status_code=400, detail="无法确定社区")

    # 校验照片至少 1 张（D6 阶段；当前只校验字段）
    if body.photo_count < 1:
        pass

    # 创建活动
    # v3: organizer_branch_id / source_type 兼容字段已由 schema 自动填（source_type=organize_type）
    data = body.model_dump(
        exclude={"participants", "photo_count", "organizer_branch_id"},
    )
    activity = Activity(
        **data,
        created_by=user.id,
        status="draft",
        community_id=community_id,
        organizer_branch_id=organizer_branch_id,
    )
    db.add(activity)
    await db.flush()  # 拿 id

    # 添加参加人员
    for p in body.participants:
        db.add(
            ActivityParticipant(
                activity_id=activity.id,
                member_id=p.member_id,
                study_hours=p.study_hours,
                attendance_status=p.attendance_status,
            )
        )

    await db.commit()

    # 返回完整数据
    r = await db.execute(
        select(Activity)
        .options(
            selectinload(Activity.participants),
            selectinload(Activity.attachments),
        )
        .where(Activity.id == activity.id)
    )
    return ActivityOut.model_validate(r.scalar_one())


@router.patch("/{activity_id}", response_model=ActivityOut)
async def update_activity(
    activity_id: int,
    body: ActivityUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ActivityOut:
    """修改活动（仅 draft / rejected 状态可改）。"""
    r = await db.execute(select(Activity).where(Activity.id == activity_id))
    a = r.scalar_one_or_none()
    if not a:
        raise HTTPException(status_code=404, detail="活动不存在")

    # v3 业务校验：partial update，只对提交了的字段校验
    try:
        data = body.model_dump(exclude_unset=True)
        # 补全可能缺少的字段（用 DB 当前值）
        for k in ("organize_type", "is_centralized", "co_organize_branch_ids", "upper_org", "study_methods"):
            if k not in data:
                v = getattr(a, k, None)
                if v is not None:
                    data[k] = v
        validate_organize_and_methods(data)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    if a.status not in ("draft", "rejected"):
        raise HTTPException(status_code=400, detail="只有草稿/已驳回状态可修改")

    if user.role == User.ROLE_COMMUNITY_ORG and a.community_id != user.community_id:
        raise HTTPException(status_code=403, detail="无权修改")
    if user.role == User.ROLE_MEMBER:
        # v3: organizer_branch_id 可能为 None（上级送课），用 co_organize_branch_ids 判断
        allowed_branches = set(a.co_organize_branch_ids or [])
        if user.branch_id not in allowed_branches:
            raise HTTPException(status_code=403, detail="无权修改")

    data = body.model_dump(exclude_unset=True, exclude={"participants", "organizer_branch_id"})
    for k, v in data.items():
        setattr(a, k, v)
    # v3: 当 organize_type / co_organize_branch_ids 变化时，重算 organizer_branch_id / community_id / source_type
    # （要在 setattr 之后做，否则会被 data 覆盖）
    if "organize_type" in data or "co_organize_branch_ids" in data:
        new_org_type = a.organize_type
        if new_org_type == "self_organize":
            new_co_ids = list(a.co_organize_branch_ids or [])
            if new_co_ids:
                brs_r = await db.execute(
                    select(Branch).where(Branch.id.in_(new_co_ids))
                )
                branches = brs_r.scalars().all()
                community_ids = {b.community_id for b in branches}
                if len(community_ids) == 1:
                    a.community_id = community_ids.pop()
                a.organizer_branch_id = new_co_ids[0]
                a.source_type = "self_organize"
                a.upper_org = None
        elif new_org_type == "upper_send":
            a.organizer_branch_id = None
            a.source_type = "upper_send"
            a.co_organize_branch_ids = []

    if body.participants is not None:
        # 用 member_id 做 upsert，避免 delete+insert 触发 UNIQUE 约束
        existing_r = await db.execute(
            select(ActivityParticipant).where(ActivityParticipant.activity_id == a.id)
        )
        existing_map: dict[int, ActivityParticipant] = {p.member_id: p for p in existing_r.scalars().all()}

        new_member_ids = {p.member_id for p in body.participants}
        # 删掉不再存在的人员
        for mid, op in existing_map.items():
            if mid not in new_member_ids:
                await db.delete(op)
        # 新增或更新
        for p in body.participants:
            if p.member_id in existing_map:
                op = existing_map[p.member_id]
                op.study_hours = p.study_hours
                op.attendance_status = p.attendance_status
            else:
                db.add(
                    ActivityParticipant(
                        activity_id=a.id,
                        member_id=p.member_id,
                        study_hours=p.study_hours,
                        attendance_status=p.attendance_status,
                    )
                )
        # 更新人数
        a.participant_count = len(body.participants)

    await db.commit()

    r2 = await db.execute(
        select(Activity)
        .options(
            selectinload(Activity.participants),
            selectinload(Activity.attachments),
        )
        .where(Activity.id == a.id)
    )
    return ActivityOut.model_validate(r2.scalar_one())


@router.post("/{activity_id}/submit", response_model=ActivityOut)
async def submit_activity(
    activity_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ActivityOut:
    """提交审核（draft/rejected → pending_community）。"""
    r = await db.execute(
        select(Activity)
        .options(selectinload(Activity.attachments), selectinload(Activity.participants))
        .where(Activity.id == activity_id)
    )
    a = r.scalar_one_or_none()
    if not a:
        raise HTTPException(status_code=404, detail="活动不存在")

    if a.status not in ("draft", "rejected"):
        raise HTTPException(status_code=400, detail="只有草稿/已驳回状态可提交")

    if user.role == User.ROLE_COMMUNITY_ORG and a.community_id != user.community_id:
        raise HTTPException(status_code=403, detail="无权提交")
    if user.role == User.ROLE_MEMBER:
        # v3: organizer_branch_id 可能为 None（上级送课），用 co_organize_branch_ids 判断
        allowed_branches = set(a.co_organize_branch_ids or [])
        if user.branch_id not in allowed_branches:
            raise HTTPException(status_code=403, detail="无权提交")

    # 必须有至少 1 张现场照片
    photo_count = sum(1 for att in a.attachments if att.kind == "photo")
    if photo_count < 1:
        raise HTTPException(status_code=400, detail="必须上传至少 1 张现场照片")

    # 必须有参加人员
    if not a.participants:
        raise HTTPException(status_code=400, detail="请选择参加人员")

    a.status = "pending_community"
    a.reject_reason = None

    # 创建/更新审核流
    af_r = await db.execute(select(AuditFlow).where(AuditFlow.activity_id == a.id))
    af = af_r.scalar_one_or_none()
    if af:
        af.current_node = "community_review"
        af.status = "in_progress"
    else:
        db.add(
            AuditFlow(
                activity_id=a.id,
                current_node="community_review",
                status="in_progress",
            )
        )

    # 审核日志
    db.add(
        AuditLog(
            activity_id=a.id,
            node="community_review",
            operator_id=user.id,
            action="submit",
        )
    )

    await db.commit()

    r2 = await db.execute(
        select(Activity)
        .options(
            selectinload(Activity.participants),
            selectinload(Activity.attachments),
        )
        .where(Activity.id == a.id)
    )
    return ActivityOut.model_validate(r2.scalar_one())


@router.delete("/{activity_id}", status_code=204)
async def delete_activity(
    activity_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    """删除活动（草稿 / 已驳回状态）。"""
    r = await db.execute(select(Activity).where(Activity.id == activity_id))
    a = r.scalar_one_or_none()
    if not a:
        raise HTTPException(status_code=404, detail="活动不存在")

    if a.status not in ("draft", "rejected"):
        raise HTTPException(status_code=400, detail="只有草稿/已驳回状态可删除")

    if user.role in (User.ROLE_COMMUNITY_ORG, User.ROLE_BRANCH_SEC) and a.community_id != user.community_id:
        raise HTTPException(status_code=403, detail="无权删除")
    if user.role == User.ROLE_MEMBER:
        # v3: organizer_branch_id 可能为 None（上级送课），用 co_organize_branch_ids 判断
        allowed_branches = set(a.co_organize_branch_ids or [])
        if user.branch_id not in allowed_branches:
            raise HTTPException(status_code=403, detail="无权删除")

    await db.delete(a)
    await db.commit()


@router.post("/{activity_id}/attachments", response_model=AttachmentOut)
async def add_attachment(
    activity_id: int,
    body: AttachmentCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ActivityAttachment:
    """添加活动附件（照片/签到表）。"""
    r = await db.execute(select(Activity).where(Activity.id == activity_id))
    a = r.scalar_one_or_none()
    if not a:
        raise HTTPException(status_code=404, detail="活动不存在")

    if user.role == User.ROLE_COMMUNITY_ORG and a.community_id != user.community_id:
        raise HTTPException(status_code=403, detail="无权操作")
    if user.role == User.ROLE_MEMBER:
        # v3: organizer_branch_id 可能为 None（上级送课），用 co_organize_branch_ids 判断
        allowed_branches = set(a.co_organize_branch_ids or [])
        if user.branch_id not in allowed_branches:
            raise HTTPException(status_code=403, detail="无权操作")

    if body.kind not in ("photo", "signin"):
        raise HTTPException(status_code=400, detail="kind 必须是 photo / signin")

    att = ActivityAttachment(
        activity_id=activity_id,
        kind=body.kind,
        file_url=body.file_url,
        file_size=body.file_size,
        sort=body.sort,
        uploaded_by=user.id,
    )
    db.add(att)
    await db.commit()
    await db.refresh(att)
    return att


@router.delete("/{activity_id}/attachments", status_code=204)
async def remove_attachments(
    activity_id: int,
    kind: str | None = Query(None, description="只删该类型（photo/signin）；不传则全删"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    """批量删除活动附件（按 kind 可选过滤）。"""
    a_r = await db.execute(select(Activity).where(Activity.id == activity_id))
    a = a_r.scalar_one_or_none()
    if not a:
        raise HTTPException(status_code=404, detail="活动不存在")

    if user.role == User.ROLE_COMMUNITY_ORG and a.community_id != user.community_id:
        raise HTTPException(status_code=403, detail="无权操作")
    if user.role == User.ROLE_MEMBER:
        # v3: organizer_branch_id 可能为 None（上级送课），用 co_organize_branch_ids 判断
        allowed_branches = set(a.co_organize_branch_ids or [])
        if user.branch_id not in allowed_branches:
            raise HTTPException(status_code=403, detail="无权操作")

    if a.status not in ("draft", "rejected"):
        raise HTTPException(status_code=400, detail="草稿/已驳回状态可删除附件")

    stmt = select(ActivityAttachment).where(ActivityAttachment.activity_id == activity_id)
    if kind:
        stmt = stmt.where(ActivityAttachment.kind == kind)
    r = await db.execute(stmt)
    for att in r.scalars().all():
        await db.delete(att)
    await db.commit()


@router.delete("/{activity_id}/attachments/{attachment_id}", status_code=204)
async def remove_attachment(
    activity_id: int,
    attachment_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    """删除单个附件。"""
    r = await db.execute(
        select(ActivityAttachment).where(
            ActivityAttachment.id == attachment_id,
            ActivityAttachment.activity_id == activity_id,
        )
    )
    att = r.scalar_one_or_none()
    if not att:
        raise HTTPException(status_code=404, detail="附件不存在")

    a_r = await db.execute(select(Activity).where(Activity.id == activity_id))
    a = a_r.scalar_one()
    if user.role == User.ROLE_COMMUNITY_ORG and a.community_id != user.community_id:
        raise HTTPException(status_code=403, detail="无权操作")
    if user.role == User.ROLE_MEMBER:
        # v3: organizer_branch_id 可能为 None（上级送课），用 co_organize_branch_ids 判断
        allowed_branches = set(a.co_organize_branch_ids or [])
        if user.branch_id not in allowed_branches:
            raise HTTPException(status_code=403, detail="无权操作")

    if a.status not in ("draft", "rejected"):
        raise HTTPException(status_code=400, detail="草稿/已驳回状态可删除附件")

    await db.delete(att)
    await db.commit()
