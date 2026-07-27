"""/api/v1/orgs 组织架构路由。"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.member import Member
from app.models.party import Branch, Community, Street
from app.models.user import User
from app.schemas.org import (
    BranchCreate,
    BranchOut,
    BranchUpdate,
    CommunityCreate,
    CommunityOut,
    CommunityUpdate,
    StreetCreate,
    StreetOut,
    StreetTree,
    StreetUpdate,
)

router = APIRouter(prefix="/orgs", tags=["orgs"])

# 权限分组
# 街道：仅系统管理员
ADMIN_ONLY = (User.ROLE_ADMIN,)
# 社区/支部：系统管理员 + 街道负责人（限定在自己街道内）
ADMIN_OR_STREET_LEAD = (User.ROLE_ADMIN, User.ROLE_STREET_LEAD)


def can_manage_in_street(user: User, street_id: int | None) -> bool:
    """判断用户是否能管理指定街道下的组织。"""
    if user.role == User.ROLE_ADMIN:
        return True
    if user.role == User.ROLE_STREET_LEAD:
        return user.street_id == street_id
    return False


async def _assert_community_in_user_street(user: User, community: Community) -> None:
    """校验社区在用户的街道范围内（admin 跳过）。"""
    if user.role == User.ROLE_ADMIN:
        return
    if user.role == User.ROLE_STREET_LEAD and user.street_id == community.street_id:
        return
    raise HTTPException(status_code=403, detail="无权操作该社区（不在你的街道范围内）")


async def _assert_branch_in_user_street(user: User, branch: Branch) -> None:
    """校验支部在用户的街道范围内（admin 跳过）。"""
    if user.role == User.ROLE_ADMIN:
        return
    if user.role == User.ROLE_STREET_LEAD and user.street_id == branch.community.street_id:
        return
    raise HTTPException(status_code=403, detail="无权操作该支部（不在你的街道范围内）")


@router.get("/streets", response_model=list[StreetOut])
async def list_streets(
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> list[Street]:
    """所有街道。"""
    result = await db.execute(select(Street).order_by(Street.id))
    return list(result.scalars().all())


@router.post("/streets", response_model=StreetOut, status_code=201)
async def create_street(
    body: StreetCreate,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_roles(*ADMIN_ONLY)),
) -> Street:
    s = Street(**body.model_dump())
    db.add(s)
    await db.commit()
    await db.refresh(s)
    return s


@router.patch("/streets/{street_id}", response_model=StreetOut)
async def update_street(
    street_id: int,
    body: StreetUpdate,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_roles(*ADMIN_ONLY)),
) -> Street:
    r = await db.execute(select(Street).where(Street.id == street_id))
    s = r.scalar_one_or_none()
    if not s:
        raise HTTPException(status_code=404, detail="街道不存在")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(s, k, v)
    await db.commit()
    await db.refresh(s)
    return s


@router.delete("/streets/{street_id}", status_code=204)
async def delete_street(
    street_id: int,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_roles(*ADMIN_ONLY)),
) -> None:
    r = await db.execute(select(Street).where(Street.id == street_id))
    s = r.scalar_one_or_none()
    if not s:
        raise HTTPException(status_code=404, detail="街道不存在")
    # 检查是否有下级
    cnt = (await db.execute(
        select(func.count()).where(Community.street_id == street_id)
    )).scalar() or 0
    if cnt > 0:
        raise HTTPException(status_code=400, detail=f"该街道下还有 {cnt} 个社区，请先删除")
    await db.delete(s)
    await db.commit()


@router.get("/communities", response_model=list[CommunityOut])
async def list_communities(
    street_id: int | None = None,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> list[Community]:
    """社区列表。可选按 street_id 过滤。"""
    stmt = select(Community).order_by(Community.id)
    if street_id is not None:
        stmt = stmt.where(Community.street_id == street_id)
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.post("/communities", response_model=CommunityOut, status_code=201)
async def create_community(
    body: CommunityCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(*ADMIN_OR_STREET_LEAD)),
) -> Community:
    # 校验街道
    r = await db.execute(select(Street).where(Street.id == body.street_id))
    if not r.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="街道不存在")
    # 权限：街道负责人只能在自家街道下新增
    if not can_manage_in_street(user, body.street_id):
        raise HTTPException(status_code=403, detail="无权在该街道下新增社区")
    c = Community(**body.model_dump())
    db.add(c)
    await db.commit()
    await db.refresh(c)
    return c


@router.patch("/communities/{community_id}", response_model=CommunityOut)
async def update_community(
    community_id: int,
    body: CommunityUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(*ADMIN_OR_STREET_LEAD)),
) -> Community:
    r = await db.execute(
        select(Community).options(selectinload(Community.street)).where(Community.id == community_id)
    )
    c = r.scalar_one_or_none()
    if not c:
        raise HTTPException(status_code=404, detail="社区不存在")
    await _assert_community_in_user_street(user, c)
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(c, k, v)
    await db.commit()
    await db.refresh(c)
    return c


@router.delete("/communities/{community_id}", status_code=204)
async def delete_community(
    community_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(*ADMIN_OR_STREET_LEAD)),
) -> None:
    r = await db.execute(
        select(Community).options(selectinload(Community.street)).where(Community.id == community_id)
    )
    c = r.scalar_one_or_none()
    if not c:
        raise HTTPException(status_code=404, detail="社区不存在")
    await _assert_community_in_user_street(user, c)
    # 该社区下还有支部 → 拒绝
    branch_cnt = (await db.execute(
        select(func.count()).where(Branch.community_id == community_id)
    )).scalar() or 0
    if branch_cnt > 0:
        raise HTTPException(
            status_code=400,
            detail=f"该社区下还有 {branch_cnt} 个支部，请先删除",
        )
    # 该社区下还有活动（community_id 引用）→ 拒绝
    from sqlalchemy import text as t
    act_cnt = (await db.execute(t(
        "SELECT COUNT(*) FROM activities WHERE community_id = :cid"
    ), {"cid": community_id})).scalar() or 0
    if act_cnt > 0:
        raise HTTPException(
            status_code=400,
            detail=f"该社区下还有 {act_cnt} 个活动，请先处理",
        )
    # 该社区下还有 users（community_id 引用）→ 拒绝（这些人属于本社区，社区没了没意义）
    user_cnt = (await db.execute(
        select(func.count()).where(User.community_id == community_id)
    )).scalar() or 0
    if user_cnt > 0:
        raise HTTPException(
            status_code=400,
            detail=f"该社区下还有 {user_cnt} 个账号，请先调整或删除这些账号",
        )
    await db.delete(c)
    await db.commit()


@router.get("/branches", response_model=list[BranchOut])
async def list_branches(
    community_id: int | None = None,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> list[Branch]:
    """支部列表。可选按 community_id 过滤。"""
    stmt = select(Branch).order_by(Branch.id)
    if community_id is not None:
        stmt = stmt.where(Branch.community_id == community_id)
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.post("/branches", response_model=BranchOut, status_code=201)
async def create_branch(
    body: BranchCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(*ADMIN_OR_STREET_LEAD)),
) -> Branch:
    r = await db.execute(
        select(Community).options(selectinload(Community.street)).where(Community.id == body.community_id)
    )
    c = r.scalar_one_or_none()
    if not c:
        raise HTTPException(status_code=400, detail="社区不存在")
    # 校验：街道负责人只能在自己街道的社区下新建支部
    if not can_manage_in_street(user, c.street_id):
        raise HTTPException(status_code=403, detail="无权在该社区下新增支部")
    b = Branch(**body.model_dump())
    db.add(b)
    await db.commit()
    await db.refresh(b)
    return b


@router.patch("/branches/{branch_id}", response_model=BranchOut)
async def update_branch(
    branch_id: int,
    body: BranchUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(*ADMIN_OR_STREET_LEAD)),
) -> Branch:
    r = await db.execute(
        select(Branch).options(selectinload(Branch.community).selectinload(Community.street))
        .where(Branch.id == branch_id)
    )
    b = r.scalar_one_or_none()
    if not b:
        raise HTTPException(status_code=404, detail="支部不存在")
    await _assert_branch_in_user_street(user, b)
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(b, k, v)
    await db.commit()
    await db.refresh(b)
    return b


@router.delete("/branches/{branch_id}", status_code=204)
async def delete_branch(
    branch_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(*ADMIN_OR_STREET_LEAD)),
) -> None:
    r = await db.execute(
        select(Branch).options(selectinload(Branch.community).selectinload(Community.street))
        .where(Branch.id == branch_id)
    )
    b = r.scalar_one_or_none()
    if not b:
        raise HTTPException(status_code=404, detail="支部不存在")
    await _assert_branch_in_user_street(user, b)
    # 只统计"在册"党员（active）；已出党（dimission）的历史记录不挡组织调整
    cnt = (await db.execute(
        select(func.count()).where(
            Member.branch_id == branch_id,
            Member.status == "active",
        )
    )).scalar() or 0
    if cnt > 0:
        raise HTTPException(
            status_code=400,
            detail=f"该支部下还有 {cnt} 名在册党员，请先处理后再删除支部",
        )
    # 该支部下只有 dimission 党员 → 一并硬删（FK 约束 + 组织已无意义）
    # 同手机号的 users 也清掉（防止孤儿账号）
    from app.models.activity import ActivityParticipant
    from app.models.study import StudyHour
    from app.models.user import User

    dimission_members = (await db.execute(
        select(Member).where(
            Member.branch_id == branch_id,
            Member.status == "dimission",
        )
    )).scalars().all()
    # 该支部下只有 dimission 党员 → 一并硬删（FK 约束 + 组织已无意义）
    # 用 raw SQL 显式控制顺序：先清引用表 → 清 users → 清 members → 删 branch
    from sqlalchemy import text
    dimission_phones = [m.phone for m in dimission_members]
    dimission_ids = [m.id for m in dimission_members]
    if dimission_ids:
        ids_csv = ",".join(str(i) for i in dimission_ids)
        phones_csv = ",".join(f"'{p}'" for p in dimission_phones)
        # 0) 删掉该支部作为发起方的活动（连带参与者 / 审核流 / 附件）
        #    这些活动相关党员都已 dimission，活动本身没保留价值
        act_ids_rows = await db.execute(text(
            "SELECT id FROM activities WHERE organizer_branch_id = :bid"
        ), {"bid": branch_id})
        act_ids = [r[0] for r in act_ids_rows.fetchall()]
        if act_ids:
            act_csv = ",".join(str(i) for i in act_ids)
            await db.execute(text(
                f"DELETE FROM activity_attachments WHERE activity_id IN ({act_csv})"
            ))
            await db.execute(text(
                f"DELETE FROM activity_participants WHERE activity_id IN ({act_csv})"
            ))
            await db.execute(text(
                f"DELETE FROM audit_flows WHERE activity_id IN ({act_csv})"
            ))
            await db.execute(text(
                f"DELETE FROM audit_logs WHERE activity_id IN ({act_csv})"
            ))
            await db.execute(text(
                "DELETE FROM activities WHERE organizer_branch_id = :bid"
            ), {"bid": branch_id})
        # 1) 清 activity_participants 引用本支部 dimission 党员
        await db.execute(text(
            f"DELETE FROM activity_participants WHERE member_id IN ({ids_csv})"
        ))
        # 2) 清 study_hours
        await db.execute(text(
            f"DELETE FROM study_hours WHERE member_id IN ({ids_csv})"
        ))
        # 3) 清 user：分两路
        if dimission_phones:
            await db.execute(text(
                f"DELETE FROM users WHERE phone IN ({phones_csv})"
            ))
        await db.execute(text(
            "DELETE FROM users WHERE branch_id = :bid"
        ), {"bid": branch_id})
        # 4) 清 members
        await db.execute(text(
            "DELETE FROM members WHERE branch_id = :bid"
        ), {"bid": branch_id})
        await db.flush()
    # 5) 删 branch
    await db.delete(b)
    await db.commit()


@router.get("/tree", response_model=list[StreetTree])
async def get_org_tree(
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> list[Street]:
    """完整组织架构树：街道 → 社区 → 支部。"""
    result = await db.execute(
        select(Street)
        .options(
            selectinload(Street.communities).selectinload(Community.branches)
        )
        .order_by(Street.id)
    )
    return list(result.scalars().unique().all())


@router.get("/my-scope")
async def get_my_scope(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """当前用户的数据范围（按 role 决定可见层级）。"""
    if user.role in (User.ROLE_ADMIN, User.ROLE_STREET_LEAD):
        # 全街道
        return {
            "scope": "street",
            "street_id": user.street_id,
            "community_id": None,
            "branch_id": None,
        }
    if user.role == User.ROLE_COMMUNITY_ORG:
        return {
            "scope": "community",
            "street_id": user.street_id,
            "community_id": user.community_id,
            "branch_id": None,
        }
    if user.role == User.ROLE_BRANCH_SEC:
        return {
            "scope": "branch",
            "street_id": user.street_id,
            "community_id": user.community_id,
            "branch_id": user.branch_id,
        }
    if user.role == User.ROLE_MEMBER:
        return {
            "scope": "self",
            "street_id": user.street_id,
            "community_id": user.community_id,
            "branch_id": user.branch_id,
        }
    raise HTTPException(status_code=400, detail="未知角色")
