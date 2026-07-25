"""/api/v1/orgs 组织架构路由。"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.party import Branch, Community, Street
from app.models.user import User
from app.schemas.org import BranchOut, CommunityOut, StreetOut, StreetTree

router = APIRouter(prefix="/orgs", tags=["orgs"])


@router.get("/streets", response_model=list[StreetOut])
async def list_streets(
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> list[Street]:
    """所有街道。"""
    result = await db.execute(select(Street).order_by(Street.id))
    return list(result.scalars().all())


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
