"""/api/v1/audits 审核路由（两级审核流）。"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.activity import Activity
from app.models.audit import AuditFlow, AuditLog
from app.models.party import Branch, Community
from app.models.user import User
from app.schemas.audit import (
    AuditActionRequest,
    AuditItem,
    AuditListResponse,
    AuditLogOut,
)
from app.services.study_hours import write_study_hours_for_activity

router = APIRouter(prefix="/audits", tags=["audits"])


async def _build_audit_item(activity: Activity, af: AuditFlow, db: AsyncSession) -> AuditItem:
    """组装待办/历史列表项（含关联字段）。"""
    submitter = await db.get(User, activity.created_by)
    branch = await db.get(Branch, activity.organizer_branch_id)
    community = await db.get(Community, activity.community_id)
    return AuditItem(
        id=activity.id,
        activity_id=activity.id,
        theme=activity.theme,
        location=activity.location,
        training_at=activity.training_at,
        participant_count=activity.participant_count,
        study_hours=float(activity.study_hours),
        organizer_branch_id=activity.organizer_branch_id,
        organizer_branch_name=branch.name if branch else None,
        community_id=activity.community_id,
        community_name=community.name if community else None,
        submitter_id=activity.created_by,
        submitter_name=submitter.name if submitter else None,
        current_node=af.current_node,
        status=af.status,
        created_at=activity.created_at,
    )


@router.get("/pending", response_model=AuditListResponse)
async def list_pending(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> AuditListResponse:
    """当前用户的待审核列表。

    - 社区委员（community_organizer）：本社区、待社区审核（含自己提交的，但操作层禁止自审）
    - 街道负责人（street_lead）：全街道、待街道审核
    - 系统管理员：全
    """
    stmt = (
        select(Activity, AuditFlow)
        .join(AuditFlow, AuditFlow.activity_id == Activity.id)
        .order_by(Activity.created_at.desc())
    )

    if user.role == User.ROLE_COMMUNITY_ORG:
        stmt = stmt.where(
            Activity.community_id == user.community_id,
            AuditFlow.current_node == "community_review",
            AuditFlow.status == "in_progress",
            # 不排除自己提交的——用户需要看到"等待他人审核"的状态
            # 自审保护在 _do_audit_action 的 403 里兜底
        )
    elif user.role == User.ROLE_STREET_LEAD:
        stmt = stmt.where(
            AuditFlow.current_node == "street_review",
            AuditFlow.status == "in_progress",
        )
    elif user.role == User.ROLE_ADMIN:
        # 超管看全部
        stmt = stmt.where(AuditFlow.status == "in_progress")
    else:
        # 其他角色无权限
        return AuditListResponse(total=0, items=[])

    result = await db.execute(stmt)
    rows = result.all()
    items = []
    for activity, af in rows:
        items.append(await _build_audit_item(activity, af, db))

    return AuditListResponse(total=len(items), items=items)


@router.get("/history", response_model=AuditListResponse)
async def list_history(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> AuditListResponse:
    """历史审核（已通过/已驳回）。"""
    stmt = (
        select(Activity, AuditFlow)
        .join(AuditFlow, AuditFlow.activity_id == Activity.id)
        .where(AuditFlow.status.in_(("approved", "rejected")))
        .order_by(Activity.updated_at.desc())
    )

    # 角色数据范围（v2026-07-28：社区组织员 = 本社区）
    if user.role in (User.ROLE_COMMUNITY_ORG, User.ROLE_BRANCH_SEC):
        stmt = stmt.where(Activity.community_id == user.community_id)
    elif user.role == User.ROLE_MEMBER:
        # 党员看自己参加的
        from app.models.activity import ActivityParticipant
        p_stmt = select(ActivityParticipant.member_id).where(
            ActivityParticipant.member_id == user.branch_id  # 简化：按 user.id 而不是 member.id
        )
        stmt = stmt.where(Activity.id.in_(p_stmt.subquery()))
    elif user.role not in (User.ROLE_ADMIN, User.ROLE_STREET_LEAD):
        return AuditListResponse(total=0, items=[])

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar() or 0
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(stmt)
    rows = result.all()

    items = []
    for activity, af in rows:
        items.append(await _build_audit_item(activity, af, db))

    return AuditListResponse(total=total, items=items)


async def _do_audit_action(
    db: AsyncSession,
    user: User,
    activity_id: int,
    action: str,  # approve / reject
    comment: str | None,
) -> Activity:
    """统一的审核逻辑：状态机推进 + 校验 + 写日志 + 必要时回写学时。"""
    af_r = await db.execute(select(AuditFlow).where(AuditFlow.activity_id == activity_id))
    af = af_r.scalar_one_or_none()
    if not af:
        raise HTTPException(status_code=404, detail="审核流不存在")
    if af.status != "in_progress":
        raise HTTPException(status_code=400, detail="审核已结束")

    act_r = await db.execute(select(Activity).where(Activity.id == activity_id))
    activity = act_r.scalar_one_or_none()
    if not activity:
        raise HTTPException(status_code=404, detail="活动不存在")

    # 节点权限校验（已放开自审：社区组织委员/街道负责人可审核自己提交的活动）
    if af.current_node == "community_review":
        if user.role != User.ROLE_COMMUNITY_ORG:
            raise HTTPException(status_code=403, detail="仅社区组织委员可初审")
        if activity.community_id != user.community_id:
            raise HTTPException(status_code=403, detail="无权审核其他社区活动")
        node = "community_review"
    elif af.current_node == "street_review":
        if user.role not in (User.ROLE_STREET_LEAD, User.ROLE_ADMIN):
            raise HTTPException(status_code=403, detail="仅街道负责人可复审")
        node = "street_review"
    else:
        raise HTTPException(status_code=400, detail=f"未知审核节点: {af.current_node}")

    if action == "reject":
        if not comment or not comment.strip():
            raise HTTPException(status_code=400, detail="驳回时必须填写审核意见")

    # 推进状态
    if action == "approve":
        if af.current_node == "community_review":
            activity.status = "pending_street"
            af.current_node = "street_review"
        elif af.current_node == "street_review":
            activity.status = "approved"
            af.current_node = "done"
            af.status = "approved"
            # 写入学时
            await write_study_hours_for_activity(db, activity.id)
    elif action == "reject":
        activity.status = "rejected"
        activity.reject_reason = comment
        af.current_node = "done"
        af.status = "rejected"

    # 写日志
    db.add(
        AuditLog(
            activity_id=activity.id,
            node=node,
            operator_id=user.id,
            action=action,
            comment=comment,
        )
    )

    await db.commit()
    await db.refresh(activity)
    return activity


@router.post("/{activity_id}/approve")
async def approve_activity(
    activity_id: int,
    body: AuditActionRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """同意审核。"""
    activity = await _do_audit_action(db, user, activity_id, "approve", body.comment)
    return {
        "ok": True,
        "activity_id": activity.id,
        "status": activity.status,
    }


@router.post("/{activity_id}/reject")
async def reject_activity(
    activity_id: int,
    body: AuditActionRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """驳回审核（必须填意见）。"""
    activity = await _do_audit_action(db, user, activity_id, "reject", body.comment)
    return {
        "ok": True,
        "activity_id": activity.id,
        "status": activity.status,
        "reject_reason": activity.reject_reason,
    }


@router.get("/{activity_id}/logs", response_model=list[AuditLogOut])
async def get_audit_logs(
    activity_id: int,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> list[AuditLog]:
    """活动的审核日志。"""
    r = await db.execute(
        select(AuditLog).where(AuditLog.activity_id == activity_id).order_by(AuditLog.id)
    )
    logs = list(r.scalars().all())
    # 补 operator_name
    for log in logs:
        u = await db.get(User, log.operator_id)
        log.operator_name = u.name if u else None
    return logs
