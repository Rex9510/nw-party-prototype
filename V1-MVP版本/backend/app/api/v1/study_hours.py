"""/api/v1/study-hours 学时档案路由。"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.activity import Activity, ActivityParticipant
from app.models.member import Member
from app.models.party import Branch
from app.models.study import StudyHour
from app.models.user import User
from app.schemas.study import StudyDetailItem, StudyDetailResponse, StudyHourListResponse, StudyHourListItem
from app.services.permissions import get_member_scope_filter

router = APIRouter(prefix="/study-hours", tags=["study-hours"])


@router.get("", response_model=StudyHourListResponse)
async def list_study_hours(
    year: int = Query(..., description="查询年份"),
    community_id: int | None = None,
    branch_id: int | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> StudyHourListResponse:
    """按年度统计所有党员的学时。"""
    stmt = select(StudyHour, Member, Branch).join(
        Member, Member.id == StudyHour.member_id
    ).outerjoin(Branch, Branch.id == Member.branch_id).where(StudyHour.year == year)

    # 角色数据范围
    scope = get_member_scope_filter(user)
    if "branch_id" in scope and scope["branch_id"]:
        stmt = stmt.where(Member.branch_id == scope["branch_id"])
    elif "community_id" in scope and scope["community_id"]:
        stmt = stmt.where(Branch.community_id == scope["community_id"])
    elif "street_id" in scope and scope["street_id"]:
        from app.models.party import Community
        stmt = stmt.join(Community, Community.id == Branch.community_id).where(
            Community.street_id == scope["street_id"]
        )

    if community_id:
        stmt = stmt.where(Branch.community_id == community_id)
    if branch_id:
        stmt = stmt.where(Member.branch_id == branch_id)

    stmt = stmt.order_by(StudyHour.total_hours.desc())
    result = await db.execute(stmt)
    rows = result.all()

    items = [
        StudyHourListItem(
            member_id=sh.member_id,
            member_name=m.name,
            member_phone=m.phone,
            branch_name=b.name if b else None,
            year=sh.year,
            total_hours=sh.total_hours,
            activity_count=sh.activity_count,
        )
        for sh, m, b in rows
    ]
    return StudyHourListResponse(year=year, total_members=len(items), items=items)


@router.get("/me", response_model=StudyDetailResponse)
async def get_my_study(
    year: int = Query(..., description="查询年份"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> StudyDetailResponse:
    """当前用户的学时档案。"""
    # 用户可能没有关联 member 记录（管理员等），这种情况下返回空
    # 简化：按 user.id 找 member（如果手机号匹配）
    mr = await db.execute(select(Member).where(Member.phone == user.phone, Member.status == "active"))
    member = mr.scalar_one_or_none()

    if not member:
        return StudyDetailResponse(
            member_id=0,
            member_name=user.name,
            year=year,
            total_hours=0,
            activity_count=0,
            items=[],
        )

    return await _build_detail(db, member, year)


@router.get("/{member_id}", response_model=StudyDetailResponse)
async def get_member_study(
    member_id: int,
    year: int = Query(..., description="查询年份"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> StudyDetailResponse:
    """查询指定党员的学时档案。"""
    mr = await db.execute(select(Member).where(Member.id == member_id))
    member = mr.scalar_one_or_none()
    if not member:
        raise HTTPException(status_code=404, detail="党员不存在")

    # 权限
    if user.role == User.ROLE_COMMUNITY_ORG:
        br = await db.get(Branch, member.branch_id)
        if not br or br.community_id != user.community_id:
            raise HTTPException(status_code=403, detail="无权查看")
    elif user.role in (User.ROLE_BRANCH_SEC,):
        if member.branch_id != user.branch_id:
            raise HTTPException(status_code=403, detail="无权查看")
    elif user.role == User.ROLE_MEMBER:
        # 党员只能看自己（按手机号匹配）
        if member.phone != user.phone:
            raise HTTPException(status_code=403, detail="无权查看他人档案")

    return await _build_detail(db, member, year)


async def _build_detail(db: AsyncSession, member: Member, year: int) -> StudyDetailResponse:
    """组装个人明细：当年所有参与过的活动。"""
    sh_r = await db.execute(
        select(StudyHour).where(StudyHour.member_id == member.id, StudyHour.year == year)
    )
    sh = sh_r.scalar_one_or_none()

    p_r = await db.execute(
        select(ActivityParticipant, Activity)
        .join(Activity, Activity.id == ActivityParticipant.activity_id)
        .where(ActivityParticipant.member_id == member.id)
        .where(Activity.status == "approved")
        .order_by(Activity.training_at.desc())
    )
    rows = p_r.all()

    items = [
        StudyDetailItem(
            activity_id=act.id,
            theme=act.theme,
            training_at=act.training_at,
            location=act.location,
            study_hours=p.study_hours,
            status=act.status,
            attendance_status=p.attendance_status,
        )
        for p, act in rows
    ]

    # 只统计 year 内的活动
    year_items = [i for i in items if i.training_at.year == year]
    total_hours = sum(i.study_hours for i in year_items)

    return StudyDetailResponse(
        member_id=member.id,
        member_name=member.name,
        year=year,
        total_hours=total_hours,
        activity_count=len(year_items),
        items=year_items,
    )
