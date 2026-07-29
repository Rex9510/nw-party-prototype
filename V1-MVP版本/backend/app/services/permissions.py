"""角色权限：根据 user role 计算数据范围。

v2026-07-28 升级：
- branch_secretary（社区组织员）：从「本支部权限」升级为「本社区权限」
  与 community_organizer 行为一致：能看/管本社区所有 + 本社区下所有支部
  （用户角色 enum 值保持不变；DB 数据不需要迁移；只是权限判断逻辑升级）
"""
from app.models.user import User


def get_member_scope_filter(user: User) -> dict:
    """
    返回 SQLAlchemy 过滤条件 dict（用于 query.where(**filter)）。
    - street_lead / system_admin：全街道（不限制 community）
    - community_organizer / branch_secretary：本社区
    - member：本支部
    """
    role = user.role

    if role in (User.ROLE_ADMIN, User.ROLE_STREET_LEAD):
        return {"street_id": user.street_id} if user.street_id else {}

    if role in (User.ROLE_COMMUNITY_ORG, User.ROLE_BRANCH_SEC):
        return {"community_id": user.community_id} if user.community_id else {}

    if role == User.ROLE_MEMBER:
        return {"branch_id": user.branch_id} if user.branch_id else {}

    return {}


def can_manage_members(user: User) -> bool:
    """哪些角色能管理党员库（任何范围）。"""
    return user.role in (
        User.ROLE_ADMIN,
        User.ROLE_STREET_LEAD,
        User.ROLE_COMMUNITY_ORG,
        User.ROLE_BRANCH_SEC,  # 社区组织员可在本社区内管理
    )


def can_create_member_in(user: User, branch_community_id: int) -> bool:
    """判断 user 能否在指定支部新增党员。"""
    if not can_manage_members(user):
        return False
    if user.role in (User.ROLE_COMMUNITY_ORG, User.ROLE_BRANCH_SEC):
        # v2026-07-28 升级：社区组织员可在本社区下任何支部新增
        return user.community_id == branch_community_id
    return True


def can_create_member_at(user: User, org_level: str, *, branch_community_id: int | None = None,
                          target_street_id: int | None = None,
                          target_community_id: int | None = None) -> bool:
    """判断 user 能否在指定 org_level 的组织下新增党员。
    - org_level=branch: 需要 user 在本社区
    - org_level=community: 需要 user.community_id == target_community_id
    - org_level=street: 需要 user.street_id == target_street_id
    """
    if not can_manage_members(user):
        return False
    if user.role in (User.ROLE_ADMIN, User.ROLE_STREET_LEAD):
        return True
    if user.role in (User.ROLE_COMMUNITY_ORG, User.ROLE_BRANCH_SEC):
        # v2026-07-28 升级：社区组织员可在本社区/本社区下任何支部
        if org_level == "community":
            return user.community_id == target_community_id
        if org_level == "branch":
            return user.community_id == branch_community_id
        if org_level == "street":
            return user.street_id == target_street_id
    return False


def can_manage_member_in(user: User, target_branch_id: int, target_community_id: int | None = None) -> bool:
    """判断 user 能否管理（编辑/删除）指定支部的党员。"""
    if not can_manage_members(user):
        return False
    if user.role in (User.ROLE_ADMIN, User.ROLE_STREET_LEAD):
        return True
    if user.role in (User.ROLE_COMMUNITY_ORG, User.ROLE_BRANCH_SEC):
        # v2026-07-28 升级：社区组织员可管本社区下任何支部
        return user.community_id == target_community_id
    return False


def can_manage_member_at(user: User, m) -> bool:
    """根据党员的 org_level + 组织 ID 判断 user 能否管理这条党员。
    m: Member 实例（需有 org_level + branch_id/community_id/street_id）。
    """
    if not can_manage_members(user):
        return False
    if user.role in (User.ROLE_ADMIN, User.ROLE_STREET_LEAD):
        return True
    if user.role in (User.ROLE_COMMUNITY_ORG, User.ROLE_BRANCH_SEC):
        # v2026-07-28 升级：社区组织员可管本社区下所有（含 org_level=community/branch）
        if m.org_level == "street":
            return user.street_id == m.street_id
        if m.org_level == "community":
            return user.community_id == m.community_id
        if m.org_level == "branch":
            return user.community_id == m.branch.community_id if m.branch else False
    return False
