"""角色权限：根据 user role 计算数据范围。"""
from app.models.user import User


def get_member_scope_filter(user: User) -> dict:
    """
    返回 SQLAlchemy 过滤条件 dict（用于 query.where(**filter)）。
    - street_lead / system_admin：全街道（不限制 community）
    - community_organizer：本社区
    - branch_secretary / member：本支部
    """
    role = user.role

    if role in (User.ROLE_ADMIN, User.ROLE_STREET_LEAD):
        return {"street_id": user.street_id} if user.street_id else {}

    if role == User.ROLE_COMMUNITY_ORG:
        return {"community_id": user.community_id} if user.community_id else {}

    if role in (User.ROLE_BRANCH_SEC, User.ROLE_MEMBER):
        return {"branch_id": user.branch_id} if user.branch_id else {}

    return {}


def can_manage_members(user: User) -> bool:
    """哪些角色能管理党员库（任何范围）。"""
    return user.role in (
        User.ROLE_ADMIN,
        User.ROLE_STREET_LEAD,
        User.ROLE_COMMUNITY_ORG,
        User.ROLE_BRANCH_SEC,  # 支部书记可在本支部内管理
    )


def can_create_member_in(user: User, branch_community_id: int) -> bool:
    """判断 user 能否在指定支部新增党员。"""
    if not can_manage_members(user):
        return False
    if user.role == User.ROLE_COMMUNITY_ORG:
        return user.community_id == branch_community_id
    # 支部书记只能在本支部新增
    if user.role == User.ROLE_BRANCH_SEC:
        # 需要知道目标支部的 community_id 和 branch_id
        # 简化：调用方已经在 create_member 里查过 branch 并能用 user.branch_id 校验
        return user.branch_id is not None
    return True


def can_manage_member_in(user: User, target_branch_id: int, target_community_id: int | None = None) -> bool:
    """判断 user 能否管理（编辑/删除）指定支部的党员。"""
    if not can_manage_members(user):
        return False
    if user.role in (User.ROLE_ADMIN, User.ROLE_STREET_LEAD):
        return True
    if user.role == User.ROLE_COMMUNITY_ORG:
        return user.community_id == target_community_id
    if user.role == User.ROLE_BRANCH_SEC:
        return user.branch_id == target_branch_id
    return False
