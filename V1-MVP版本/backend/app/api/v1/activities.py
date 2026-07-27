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

    # 权限校验
    if user.role == User.ROLE_COMMUNITY_ORG and a.community_id != user.community_id:
        raise HTTPException(status_code=403, detail="无权查看")
    if user.role in (User.ROLE_BRANCH_SEC, User.ROLE_MEMBER) and a.organizer_branch_id != user.branch_id:
        raise HTTPException(status_code=403, detail="无权查看")

    # 查参与党员的名字/电话
    member_ids = [p.member_id for p in a.participants]
    member_map: dict[int, Member] = {}
    if member_ids:
        mr = await db.execute(select(Member).where(Member.id.in_(member_ids)))
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
        )
        for p in a.participants
    ]
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

    # 校验支部存在 + 权限
    br_r = await db.execute(select(Branch).where(Branch.id == body.organizer_branch_id))
    branch = br_r.scalar_one_or_none()
    if not branch:
        raise HTTPException(status_code=400, detail="支部不存在")
    if user.role == User.ROLE_COMMUNITY_ORG and user.community_id != branch.community_id:
        raise HTTPException(status_code=403, detail="无权在该支部录入")
    if user.role == User.ROLE_BRANCH_SEC and user.branch_id != body.organizer_branch_id:
        raise HTTPException(status_code=403, detail="只能在本支部录入活动")

    # 自动从支部得到 community_id
    community_id = branch.community_id

    # 校验照片至少 1 张（D6 阶段；当前只校验字段）
    if body.photo_count < 1:
        # 注意：photo_count 客户端上传后才知道，这里只是软校验
        # 实际校验在提交审核（submit）时做
        pass

    # 创建活动
    data = body.model_dump(exclude={"participants", "photo_count"})
    activity = Activity(**data, created_by=user.id, status="draft", community_id=community_id)
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

    if a.status not in ("draft", "rejected"):
        raise HTTPException(status_code=400, detail="只有草稿/已驳回状态可修改")

    if user.role == User.ROLE_COMMUNITY_ORG and a.community_id != user.community_id:
        raise HTTPException(status_code=403, detail="无权修改")
    if user.role == User.ROLE_BRANCH_SEC and a.organizer_branch_id != user.branch_id:
        raise HTTPException(status_code=403, detail="无权修改")

    data = body.model_dump(exclude_unset=True, exclude={"participants"})
    for k, v in data.items():
        setattr(a, k, v)

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
    if user.role == User.ROLE_BRANCH_SEC and a.organizer_branch_id != user.branch_id:
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
    """删除活动（仅草稿状态）。"""
    r = await db.execute(select(Activity).where(Activity.id == activity_id))
    a = r.scalar_one_or_none()
    if not a:
        raise HTTPException(status_code=404, detail="活动不存在")

    if a.status != "draft":
        raise HTTPException(status_code=400, detail="只有草稿状态可删除")

    if user.role == User.ROLE_COMMUNITY_ORG and a.community_id != user.community_id:
        raise HTTPException(status_code=403, detail="无权删除")
    if user.role == User.ROLE_BRANCH_SEC and a.organizer_branch_id != user.branch_id:
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
    if user.role == User.ROLE_BRANCH_SEC and a.organizer_branch_id != user.branch_id:
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
    if user.role == User.ROLE_BRANCH_SEC and a.organizer_branch_id != user.branch_id:
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
    if user.role == User.ROLE_BRANCH_SEC and a.organizer_branch_id != user.branch_id:
        raise HTTPException(status_code=403, detail="无权操作")

    if a.status not in ("draft", "rejected"):
        raise HTTPException(status_code=400, detail="草稿/已驳回状态可删除附件")

    await db.delete(att)
    await db.commit()
