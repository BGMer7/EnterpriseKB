"""
用户管理相关API
"""
from typing import List, Optional
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies import get_current_user, require_permission, require_admin
from app.schemas.user import (
    UserResponse, UserCreate, UserUpdate,
    UserRoleAssign, DepartmentResponse, RoleResponse
)
from app.schemas.admin import ApiResponse
from app.models.user import User
from app.core.constants import Permissions

router = APIRouter()


@router.get("", response_model=List[UserResponse])
async def list_users(
    page: int = 1,
    page_size: int = 20,
    department_id: Optional[str] = None,
    search: Optional[str] = None,
    current_user: User = Depends(
        require_permission(Permissions.USER_VIEW)
    ),
    db: AsyncSession = Depends(get_db)
):
    """
    获取用户列表
    """
    from app.services.user_service import user_service

    result = await user_service.list_users(
        db=db,
        page=page,
        page_size=page_size,
        department_id=department_id,
        search=search
    )

    return result["users"]


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str,
    current_user: User = Depends(
        require_permission(Permissions.USER_VIEW)
    ),
    db: AsyncSession = Depends(get_db)
):
    """
    获取用户详情
    """
    from app.services.user_service import user_service

    return await user_service.get_by_id(db, user_id)


@router.post("", response_model=UserResponse)
async def create_user(
    request: UserCreate,
    current_user: User = Depends(
        require_permission(Permissions.USER_CREATE)
    ),
    db: AsyncSession = Depends(get_db)
):
    """
    创建用户
    """
    from app.services.user_service import user_service

    return await user_service.create(
        db=db,
        wechat_id=request.wechat_id,
        name=request.name,
        email=request.email,
        department_id=request.department_id
    )


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    request: UserUpdate,
    current_user: User = Depends(
        require_permission(Permissions.USER_UPDATE)
    ),
    db: AsyncSession = Depends(get_db)
):
    """
    更新用户信息
    """
    from app.services.user_service import user_service

    return await user_service.update(
        db=db,
        user_id=user_id,
        update_data=request.model_dump(exclude_unset=True)
    )


@router.delete("/{user_id}")
async def delete_user(
    user_id: str,
    current_user: User = Depends(
        require_permission(Permissions.USER_DELETE)
    ),
    db: AsyncSession = Depends(get_db)
):
    """
    删除用户
    """
    from app.services.user_service import user_service

    await user_service.delete(db=db, user_id=user_id)

    return ApiResponse(message="用户删除成功")


@router.post("/{user_id}/roles")
async def assign_user_roles(
    user_id: str,
    request: UserRoleAssign,
    current_user: User = Depends(
        require_permission(Permissions.USER_UPDATE)
    ),
    db: AsyncSession = Depends(get_db)
):
    """
    分配用户角色
    """
    from app.services.user_service import user_service

    await user_service.assign_roles(
        db=db,
        user_id=user_id,
        role_ids=request.role_ids
    )

    return ApiResponse(message="角色分配成功")


# ===== 部门管理 =====
@router.get("/departments/list", response_model=List[DepartmentResponse])
async def list_departments(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    获取部门列表
    """
    from app.services.user_service import user_service

    return await user_service.list_departments(db=db)


# ===== 角色管理 =====
@router.get("/roles/list", response_model=List[RoleResponse])
async def list_roles(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    获取角色列表
    """
    from app.services.user_service import user_service

    return await user_service.list_roles(db=db)
