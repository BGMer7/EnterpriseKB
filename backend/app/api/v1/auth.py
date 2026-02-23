"""
认证相关API
"""
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies import get_current_user
from app.schemas.user import LoginRequest, LoginResponse, UserResponse
from app.models.user import User

router = APIRouter()


@router.post("/login", response_model=LoginResponse)
async def login(
    request: LoginRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    用户登录
    支持企业微信授权码登录
    """
    from app.services.auth_service import auth_service

    return await auth_service.login_with_wechat(
        db=db,
        code=request.code
    )


@router.post("/refresh")
async def refresh_token():
    """
    刷新访问Token
    """
    # TODO: 实现token刷新逻辑
    pass


@router.post("/logout")
async def logout(
    current_user: User = Depends(get_current_user)
):
    """
    用户登出
    """
    # TODO: 实现登出逻辑（清除Redis中的session）
    return {"message": "登出成功"}


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """
    获取当前用户信息
    """
    return UserResponse.model_validate(current_user)
