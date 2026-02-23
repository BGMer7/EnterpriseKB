"""
权限检查模块
实现RBAC权限控制
"""
from typing import List, Set, Optional

from app.models.user import User
from app.core.constants import Permissions, ROLE_PERMISSIONS


def get_user_permissions(user: User) -> Set[str]:
    """
    获取用户的所有权限

    Args:
        user: 用户对象

    Returns:
        Set[str]: 权限集合
    """
    permissions = set()

    # 收集所有角色的权限
    for role in user.roles:
        role_perms = ROLE_PERMISSIONS.get(role.name, [])
        permissions.update(role_perms)

    return permissions


def check_user_permission(user: User, permission: str) -> bool:
    """
    检查用户是否有指定权限

    Args:
        user: 用户对象
        permission: 权限字符串

    Returns:
        bool: 是否有权限
    """
    # 超级管理员拥有所有权限
    if is_admin(user):
        return True

    user_permissions = get_user_permissions(user)
    return permission in user_permissions


def check_user_any_permission(user: User, permissions: List[str]) -> bool:
    """
    检查用户是否有任一权限

    Args:
        user: 用户对象
        permissions: 权限列表

    Returns:
        bool: 是否有任一权限
    """
    # 超级管理员拥有所有权限
    if is_admin(user):
        return True

    user_permissions = get_user_permissions(user)
    return any(perm in user_permissions for perm in permissions)


def check_user_all_permissions(user: User, permissions: List[str]) -> bool:
    """
    检查用户是否有所有权限

    Args:
        user: 用户对象
        permissions: 权限列表

    Returns:
        bool: 是否有所有权限
    """
    # 超级管理员拥有所有权限
    if is_admin(user):
        return True

    user_permissions = get_user_permissions(user)
    return all(perm in user_permissions for perm in permissions)


def is_admin(user: User) -> bool:
    """
    检查用户是否为管理员

    Args:
        user: 用户对象

    Returns:
        bool: 是否为管理员
    """
    return any(role.name == "SUPER_ADMIN" for role in user.roles)


def is_dept_admin(user: User) -> bool:
    """
    检查用户是否为部门管理员

    Args:
        user: 用户对象

    Returns:
        bool: 是否为部门管理员
    """
    return any(role.name == "DEPT_ADMIN" for role in user.roles)


def is_content_editor(user: User) -> bool:
    """
    检查用户是否为内容编辑

    Args:
        user: 用户对象

    Returns:
        bool: 是否为内容编辑
    """
    return any(role.name == "CONTENT_EDITOR" for role in user.roles)


def get_user_role_names(user: User) -> List[str]:
    """
    获取用户角色名称列表

    Args:
        user: 用户对象

    Returns:
        List[str]: 角色名称列表
    """
    return [role.name for role in user.roles]


# ===== 文档权限检查 =====
def can_view_document(user: User, document) -> bool:
    """
    检查用户是否可以查看文档

    Args:
        user: 用户对象
        document: 文档对象

    Returns:
        bool: 是否可以查看
    """
    # 管理员可以查看所有文档
    if is_admin(user):
        return True

    # 文档是公开的
    if document.is_public:
        return True

    # 用户是上传者
    if document.uploaded_by == user.id:
        return True

    # 用户与文档同部门
    if user.department_id and document.department_id == user.department_id:
        return True

    # 用户角色在文档的允许列表中
    user_roles = get_user_role_names(user)
    if any(role in document.allowed_roles for role in user_roles):
        return True

    return False


def can_edit_document(user: User, document) -> bool:
    """
    检查用户是否可以编辑文档

    Args:
        user: 用户对象
        document: 文档对象

    Returns:
        bool: 是否可以编辑
    """
    # 需要文档编辑权限
    if not check_user_permission(user, Permissions.DOCUMENT_EDIT):
        return False

    # 管理员可以编辑所有文档
    if is_admin(user):
        return True

    # 用户是上传者
    if document.uploaded_by == user.id:
        return True

    return False


def can_delete_document(user: User, document) -> bool:
    """
    检查用户是否可以删除文档

    Args:
        user: 用户对象
        document: 文档对象

    Returns:
        bool: 是否可以删除
    """
    # 需要文档删除权限
    if not check_user_permission(user, Permissions.DOCUMENT_DELETE):
        return False

    # 管理员可以删除所有文档
    if is_admin(user):
        return True

    # 用户是上传者
    if document.uploaded_by == user.id:
        return True

    return False


# ===== 部门权限检查 =====
def can_access_department(user: User, department_id: str) -> bool:
    """
    检查用户是否可以访问部门

    Args:
        user: 用户对象
        department_id: 部门ID

    Returns:
        bool: 是否可以访问
    """
    # 管理员可以访问所有部门
    if is_admin(user):
        return True

    # 用户所属部门
    if user.department_id == department_id:
        return True

    # 部门管理员可以访问本部门
    if is_dept_admin(user):
        # 这里可以添加部门层级判断逻辑
        if user.department_id == department_id:
            return True

    return False


# ===== 搜索权限过滤器 =====
def build_search_filter(user: User) -> dict:
    """
    构建搜索权限过滤条件

    Args:
        user: 用户对象

    Returns:
        dict: 过滤条件字典
    """
    # 管理员无限制
    if is_admin(user):
        return {}

    conditions = {
        "must": []
    }

    # 公开文档
    conditions["must"].append({
        "field": "is_public",
        "value": True
    })

    # 用户所属部门
    if user.department_id:
        conditions["must"].append({
            "field": "department_id",
            "value": str(user.department_id)
        })

    # 用户角色允许的文档
    user_roles = get_user_role_names(user)
    for role in user_roles:
        conditions["must"].append({
            "field": "allowed_roles",
            "value": role
        })

    return conditions
