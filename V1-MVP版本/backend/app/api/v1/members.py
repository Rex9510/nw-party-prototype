"""/api/v1/members 党员库路由。"""
import math
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.member import Member
from app.models.party import Branch
from app.models.user import User
from app.schemas.member import (
    MemberCreate,
    MemberListItem,
    MemberListResponse,
    MemberOut,
    MemberUpdate,
)
from app.services.member_import import (
    generate_template_xlsx,
    parse_and_import,
)
from app.services.permissions import (
    can_create_member_in,
    can_manage_members,
    get_member_scope_filter,
)

router = APIRouter(prefix="/members", tags=["members"])


@router.get("/template")
async def download_template(_user: User = Depends(get_current_user)) -> StreamingResponse:
    """下载党员导入模板 xlsx。"""
    content = generate_template_xlsx()
    return StreamingResponse(
        iter([content]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": 'attachment; filename="members_template.xlsx"',
            "Content-Length": str(len(content)),
        },
    )


@router.post("/import")
async def import_members(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """批量导入党员（xlsx）。

    - 全有全无：任一行失败整文件回滚
    - 返回 total_rows / success_rows / failed_rows / error_log
    """
    if not can_manage_members(user):
        raise HTTPException(status_code=403, detail="无权导入党员")

    if not file.filename or not file.filename.lower().endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="仅支持 .xlsx / .xls 文件")

    content = await file.read()
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="文件超过 5MB")

    result = await parse_and_import(db, content, user)

    return {
        "total_rows": result.total_rows,
        "success_rows": result.success_rows,
        "failed_rows": result.failed_rows,
        "error_log": [
            {"row": e.row, "phone": e.phone, "errors": e.errors}
            for e in result.error_log
        ],
        "file_url": file.filename,
    }


@router.get("", response_model=MemberListResponse)
async def list_members(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    branch_id: int | None = None,
    community_id: int | None = None,
    keyword: str | None = None,
    status_filter: str = Query("active", alias="status", description="默认只显示在职"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> MemberListResponse:
    """党员列表（分页 + 按角色过滤）。"""
    # 基础过滤
    stmt = select(Member).options(selectinload(Member.branch))

    # 角色权限隔离
    scope = get_member_scope_filter(user)
    if "branch_id" in scope and scope["branch_id"]:
        if branch_id and branch_id != scope["branch_id"]:
            raise HTTPException(status_code=403, detail="无权访问该支部数据")
        stmt = stmt.where(Member.branch_id == scope["branch_id"])
    elif "community_id" in scope and scope["community_id"]:
        # 通过 join branch 过滤
        stmt = stmt.join(Branch, Member.branch_id == Branch.id).where(
            Branch.community_id == scope["community_id"]
        )
        if branch_id:
            stmt = stmt.where(Member.branch_id == branch_id)
    elif "street_id" in scope and scope["street_id"]:
        stmt = stmt.join(Branch, Member.branch_id == Branch.id).join(
            __import__("app.models.party", fromlist=["Community"]).Community,
            Branch.community_id == __import__("app.models.party", fromlist=["Community"]).Community.id,
        ).where(
            __import__("app.models.party", fromlist=["Community"]).Community.street_id
            == scope["street_id"]
        )
        if community_id:
            stmt = stmt.where(Branch.community_id == community_id)
        if branch_id:
            stmt = stmt.where(Member.branch_id == branch_id)

    # 关键字搜索（姓名/手机号）
    if keyword:
        like = f"%{keyword}%"
        stmt = stmt.where(or_(Member.name.like(like), Member.phone.like(like)))

    # 状态过滤
    if status_filter:
        stmt = stmt.where(Member.status == status_filter)

    # 总数
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar() or 0

    # 分页
    stmt = stmt.order_by(Member.id.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(stmt)
    members = result.scalars().all()

    items = [
        MemberListItem(
            id=m.id,
            name=m.name,
            phone=m.phone,
            id_card_no=m.id_card_no,
            gender=m.gender,
            join_date=m.join_date,
            status=m.status,
            branch_id=m.branch_id,
            branch_name=m.branch.name if m.branch else None,
            created_at=m.created_at,
            updated_at=m.updated_at,
        )
        for m in members
    ]

    return MemberListResponse(total=total, items=items)


@router.get("/{member_id}", response_model=MemberListItem)
async def get_member(
    member_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> MemberListItem:
    result = await db.execute(
        select(Member).options(selectinload(Member.branch)).where(Member.id == member_id)
    )
    m = result.scalar_one_or_none()
    if not m:
        raise HTTPException(status_code=404, detail="党员不存在")

    # 权限校验：是否在用户可见范围
    if user.role == User.ROLE_COMMUNITY_ORG:
        if m.branch and m.branch.community_id != user.community_id:
            raise HTTPException(status_code=403, detail="无权访问")
    elif user.role in (User.ROLE_BRANCH_SEC, User.ROLE_MEMBER):
        if m.branch_id != user.branch_id:
            raise HTTPException(status_code=403, detail="无权访问")

    return MemberListItem(
        id=m.id, name=m.name, phone=m.phone, id_card_no=m.id_card_no,
        gender=m.gender, join_date=m.join_date, status=m.status,
        branch_id=m.branch_id, branch_name=m.branch.name if m.branch else None,
        created_at=m.created_at, updated_at=m.updated_at,
    )


@router.post("", response_model=MemberOut, status_code=status.HTTP_201_CREATED)
async def create_member(
    body: MemberCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> MemberOut:
    if not can_manage_members(user):
        raise HTTPException(status_code=403, detail="无权新增党员")

    # 校验支部存在
    branch_r = await db.execute(select(Branch).where(Branch.id == body.branch_id))
    branch = branch_r.scalar_one_or_none()
    if not branch:
        raise HTTPException(status_code=400, detail="支部不存在")

    # 权限：社区委员只能在本社区
    if not can_create_member_in(user, branch.community_id):
        raise HTTPException(status_code=403, detail="无权在该支部新增党员")

    # 手机号唯一（active 状态）
    dup_r = await db.execute(
        select(Member).where(Member.phone == body.phone, Member.status == "active")
    )
    if dup_r.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="该手机号已存在（active 党员）")

    m = Member(**body.model_dump(), created_by=user.id)
    db.add(m)
    await db.commit()
    await db.refresh(m)
    return MemberOut.model_validate(m)


@router.patch("/{member_id}", response_model=MemberOut)
async def update_member(
    member_id: int,
    body: MemberUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> MemberOut:
    if not can_manage_members(user):
        raise HTTPException(status_code=403, detail="无权修改党员")

    r = await db.execute(select(Member).where(Member.id == member_id))
    m = r.scalar_one_or_none()
    if not m:
        raise HTTPException(status_code=404, detail="党员不存在")

    # 权限：必须在可见范围
    scope = get_member_scope_filter(user)
    if "branch_id" in scope and m.branch_id != scope["branch_id"]:
        raise HTTPException(status_code=403, detail="无权修改该党员")
    if "community_id" in scope:
        br_r = await db.execute(select(Branch).where(Branch.id == m.branch_id))
        br = br_r.scalar_one_or_none()
        if not br or br.community_id != scope["community_id"]:
            raise HTTPException(status_code=403, detail="无权修改该党员")

    data = body.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(m, k, v)
    await db.commit()
    await db.refresh(m)
    return MemberOut.model_validate(m)


@router.delete("/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_member(
    member_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    if not can_manage_members(user):
        raise HTTPException(status_code=403, detail="无权删除党员")

    r = await db.execute(select(Member).where(Member.id == member_id))
    m = r.scalar_one_or_none()
    if not m:
        raise HTTPException(status_code=404, detail="党员不存在")

    # 软删除：把 status 改为 dimission
    m.status = "dimission"
    await db.commit()
