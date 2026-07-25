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
    """哪些角色能管理党员库。"""
    return user.role in (
        User.ROLE_ADMIN,
        User.ROLE_STREET_LEAD,
        User.ROLE_COMMUNITY_ORG,
    )


def can_create_member_in(user: User, branch_community_id: int) -> bool:
    """判断 user 能否在指定支部新增党员。"""
    if not can_manage_members(user):
        return False
    if user.role == User.ROLE_COMMUNITY_ORG:
        return user.community_id == branch_community_id
    return True
