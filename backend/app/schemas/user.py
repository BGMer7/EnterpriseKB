"""
用户相关Schema
"""
from typing import Optional, List
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field


# ===== 基础Schema =====
class UserBase(BaseModel):
    """用户基础Schema"""
    name: str = Field(..., min_length=1, max_length=100)
    email: Optional[EmailStr] = None


class UserCreate(UserBase):
    """创建用户Schema"""
    wechat_id: str = Field(..., min_length=1, max_length=64)
    department_id: Optional[str] = None


class UserUpdate(BaseModel):
    """更新用户Schema"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    email: Optional[EmailStr] = None
    department_id: Optional[str] = None
    is_active: Optional[bool] = None


class UserInDB(UserBase):
    """数据库中的用户Schema"""
    id: str
    wechat_id: str
    department_id: Optional[str] = None
    avatar_url: Optional[str] = None
    is_active: bool
    last_login_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class UserResponse(UserInDB):
    """用户响应Schema"""
    roles: List[str] = []

    class Config:
        from_attributes = True


class UserWithRoles(UserResponse):
    """带详细角色的用户响应Schema"""
    roles: List[dict] = []


# ===== 登录/认证相关 =====
class LoginRequest(BaseModel):
    """登录请求Schema"""
    code: str  # 企业微信授权码


class LoginResponse(BaseModel):
    """登录响应Schema"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse


class TokenPayload(BaseModel):
    """Token载荷Schema"""
    sub: str  # 用户ID
    exp: int
    iat: int
    type: str


# ===== 部门相关 =====
class DepartmentBase(BaseModel):
    """部门基础Schema"""
    name: str = Field(..., min_length=1, max_length=100)
    code: str = Field(..., min_length=1, max_length=20)


class DepartmentCreate(DepartmentBase):
    """创建部门Schema"""
    parent_id: Optional[str] = None


class DepartmentResponse(DepartmentBase):
    """部门响应Schema"""
    id: str
    parent_id: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ===== 角色相关 =====
class RoleBase(BaseModel):
    """角色基础Schema"""
    name: str = Field(..., min_length=1, max_length=50)
    description: Optional[str] = None


class RoleCreate(RoleBase):
    """创建角色Schema"""
    permissions: List[str] = []


class RoleResponse(RoleBase):
    """角色响应Schema"""
    id: str
    permissions: List[str] = []
    created_at: datetime

    class Config:
        from_attributes = True


class UserRoleAssign(BaseModel):
    """用户角色分配Schema"""
    user_id: str
    role_ids: List[str] = []
