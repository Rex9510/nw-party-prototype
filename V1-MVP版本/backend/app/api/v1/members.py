"""/api/v1/members 党员库路由。"""
import math
import json
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.deps import get_current_user
from app.core.security import hash_password
from app.db.session import get_db
from app.models.member import Member
from app.models.party import Branch, Community
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
    can_manage_member_in,
    can_manage_members,
    get_member_scope_filter,
)


def _dump_json(v):
    """list → JSON 字符串（None 透传）。"""
    if v is None:
        return None
    return json.dumps(v, ensure_ascii=False)

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
            roles=m.roles,        # MemberOut 自动转 list
            identities=m.identities,
            photo_urls=m.photo_urls,  # 加回：让 list 头像能展示
            is_mobile_member=m.is_mobile_member,
            flow_in_date=m.flow_in_date,
            created_at=m.created_at,
            updated_at=m.updated_at,
        )
        for m in members
    ]

    return MemberListResponse(total=total, items=items)


@router.get("/by-phone/{phone}", response_model=MemberListItem)
async def get_member_by_phone(
    phone: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> MemberListItem:
    """通过手机号查党员（用于'我的'页面根据当前登录用户找到自己）。

    权限：
    - 本人（user.phone == phone）：直接可查
    - 管理员/街道：可查任意
    - 社区委员：可查本社区任意
    - 支部书记：可查本支部任意
    """
    result = await db.execute(
        select(Member).options(selectinload(Member.branch)).where(Member.phone == phone)
    )
    m = result.scalar_one_or_none()
    if not m:
        raise HTTPException(status_code=404, detail="党员档案不存在，请联系管理员")

    # 权限校验
    if user.role in (User.ROLE_ADMIN, User.ROLE_STREET_LEAD):
        pass  # 全权限
    elif user.role == User.ROLE_COMMUNITY_ORG:
        if not (m.branch and m.branch.community_id == user.community_id):
            raise HTTPException(status_code=403, detail="无权查询该党员信息")
    elif user.role == User.ROLE_BRANCH_SEC:
        if m.branch_id != user.branch_id:
            raise HTTPException(status_code=403, detail="无权查询该党员信息")
    else:  # 普通党员
        if user.phone != phone:
            raise HTTPException(status_code=403, detail="无权查询他人信息")

    return MemberListItem(
        id=m.id, name=m.name, phone=m.phone, id_card_no=m.id_card_no,
        gender=m.gender, join_date=m.join_date, status=m.status,
        branch_id=m.branch_id, branch_name=m.branch.name if m.branch else None,
        roles=m.roles, identities=m.identities,
        photo_urls=m.photo_urls,  # MemberListItem 继承自 MemberOut，自动 list
        is_mobile_member=m.is_mobile_member,
        flow_in_date=m.flow_in_date,
        created_at=m.created_at, updated_at=m.updated_at,
    )


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
        roles=m.roles, identities=m.identities, photo_urls=m.photo_urls,
        is_mobile_member=m.is_mobile_member,
        flow_in_date=m.flow_in_date,
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
    branch_r = await db.execute(
        select(Branch).options(selectinload(Branch.community)).where(Branch.id == body.branch_id)
    )
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

    # ===== 角色权限自动派发 =====
    # 前端 roles 命名 ↔ 后端 User.role 命名映射
    ROLE_FRONT_TO_BACK = {
        "system_admin": User.ROLE_ADMIN,
        "street_lead": User.ROLE_STREET_LEAD,
        "community_organizer": User.ROLE_COMMUNITY_ORG,
        "branch_secretary": User.ROLE_BRANCH_SEC,
        "party_member": User.ROLE_MEMBER,
    }
    # 权限优先级：system_admin > street_lead > community_organizer > branch_secretary > member
    ROLE_PRIORITY = [
        User.ROLE_ADMIN,
        User.ROLE_STREET_LEAD,
        User.ROLE_COMMUNITY_ORG,
        User.ROLE_BRANCH_SEC,
        User.ROLE_MEMBER,
    ]
    # 标准化 roles（统一存后端命名，前端展示再映射回前端命名）
    normalized_roles: list[str] = []
    for r in (body.roles or []):
        mapped = ROLE_FRONT_TO_BACK.get(r, r)
        if mapped not in normalized_roles:
            normalized_roles.append(mapped)
    if not normalized_roles:
        normalized_roles = [User.ROLE_MEMBER]

    chosen_role = User.ROLE_MEMBER
    for r in ROLE_PRIORITY:
        if r in normalized_roles:
            chosen_role = r
            break

    # 创建党员（含 roles/identities/photo_urls 展示字段）
    member_data = body.model_dump(exclude={"roles", "identities", "photo_urls"})
    m = Member(
        **member_data,
        roles=_dump_json(normalized_roles),
        identities=_dump_json(body.identities or []),
        photo_urls=_dump_json(body.photo_urls or []),
        created_by=user.id,
    )
    db.add(m)
    await db.commit()
    await db.refresh(m)

    # 同时创建登录账号（默认密码 = 手机号后 6 位）
    user_dup = await db.execute(
        select(User).where(User.phone == body.phone)
    )
    if user_dup.scalar_one_or_none():
        # 已有同手机号用户（极少见，可能是 admin/lead 等），跳过建账号
        return MemberOut.model_validate(m)

    default_pwd = body.phone[-6:]
    new_user = User(
        phone=body.phone,
        password_hash=hash_password(default_pwd),
        name=body.name,
        role=chosen_role,  # 按优先级自动派发
        street_id=branch.community.street_id,
        community_id=branch.community_id,
        branch_id=branch.id,
        status='active',
    )
    db.add(new_user)
    await db.commit()

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

    r = await db.execute(
        select(Member).options(selectinload(Member.branch)).where(Member.id == member_id)
    )
    m = r.scalar_one_or_none()
    if not m:
        raise HTTPException(status_code=404, detail="党员不存在")

    # 权限：必须在可见范围（按角色严格判断）
    target_community_id = m.branch.community_id if m.branch else None
    if not can_manage_member_in(user, m.branch_id, target_community_id):
        raise HTTPException(status_code=403, detail="无权修改该党员")

    # 如果 PATCH 修改了 branch_id，校验目标支部也在权限范围
    if body.branch_id is not None and body.branch_id != m.branch_id:
        new_br_r = await db.execute(
            select(Branch).options(selectinload(Branch.community)).where(Branch.id == body.branch_id)
        )
        new_br = new_br_r.scalar_one_or_none()
        if not new_br:
            raise HTTPException(status_code=400, detail="目标支部不存在")
        if not can_manage_member_in(user, new_br.id, new_br.community_id):
            raise HTTPException(status_code=403, detail="无权将党员调整到该支部")

    # 角色权限自动派发：编辑时按最新的 roles 重新算 user.role
    if body.photo_urls is not None and len(body.photo_urls) > 1:
        raise HTTPException(status_code=400, detail="风采照片最多 1 张")
    if body.roles is not None:
        ROLE_FRONT_TO_BACK = {
            "system_admin": User.ROLE_ADMIN,
            "street_lead": User.ROLE_STREET_LEAD,
            "community_organizer": User.ROLE_COMMUNITY_ORG,
            "branch_secretary": User.ROLE_BRANCH_SEC,
            "party_member": User.ROLE_MEMBER,
        }
        ROLE_PRIORITY = [
            User.ROLE_ADMIN,
            User.ROLE_STREET_LEAD,
            User.ROLE_COMMUNITY_ORG,
            User.ROLE_BRANCH_SEC,
            User.ROLE_MEMBER,
        ]
        # 标准化成后端命名再存
        normalized: list[str] = []
        for r2 in body.roles:
            mapped = ROLE_FRONT_TO_BACK.get(r2, r2)
            if mapped not in normalized:
                normalized.append(mapped)
        if not normalized:
            normalized = [User.ROLE_MEMBER]
        body.roles = normalized

        # 同步更新 user.role
        chosen = User.ROLE_MEMBER
        for rp in ROLE_PRIORITY:
            if rp in normalized:
                chosen = rp
                break
        u_r = await db.execute(select(User).where(User.phone == m.phone))
        linked_user = u_r.scalar_one_or_none()
        if linked_user:
            linked_user.role = chosen
            db.add(linked_user)

    data = body.model_dump(exclude_unset=True)
    # roles/identities/photo_urls 是 list，数据库存 JSON 字符串
    if "roles" in data and data["roles"] is not None:
        data["roles"] = _dump_json(data["roles"])
    if "identities" in data and data["identities"] is not None:
        data["identities"] = _dump_json(data["identities"])
    if "photo_urls" in data and data["photo_urls"] is not None:
        data["photo_urls"] = _dump_json(data["photo_urls"])
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

    r = await db.execute(
        select(Member).options(selectinload(Member.branch)).where(Member.id == member_id)
    )
    m = r.scalar_one_or_none()
    if not m:
        raise HTTPException(status_code=404, detail="党员不存在")

    # 权限：必须在可见范围（按角色严格判断）
    target_community_id = m.branch.community_id if m.branch else None
    if not can_manage_member_in(user, m.branch_id, target_community_id):
        raise HTTPException(status_code=403, detail="无权删除该党员")

    # 软删除：把 status 改为 dimission
    m.status = "dimission"
    await db.commit()
