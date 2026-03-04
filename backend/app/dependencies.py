"""
FastAPI依赖注入工具
"""
from typing import Generator, AsyncGenerator, Optional
from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.session import get_db_session
from app.core.security import decode_access_token
from app.models.user import User


# ===== 数据库依赖 =====
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    获取数据库会话
    使用依赖注入确保每个请求使用独立的会话
    """
    async with get_db_session() as session:
        try:
            yield session
        finally:
            await session.close()


# ===== Redis依赖 =====
async def get_redis():
    """获取Redis客户端"""
    from app.utils.cache import redis_client
    return redis_client


# ===== 用户认证依赖 =====
# 开发模式：跳过鉴权，返回默认用户
SKIP_AUTH = True  # 设置为 True 则跳过企业微信登录验证


async def get_current_user(
    db: AsyncSession = Depends(get_db),
    authorization: Optional[str] = Header(None)
) -> User:
    """
    获取当前登录用户

    Args:
        db: 数据库会话
        authorization: Authorization头 (Bearer token)

    Returns:
        User: 当前用户对象

    Raises:
        HTTPException: 认证失败时抛出401
    """
    # 开发模式：跳过鉴权，返回默认测试用户
    if SKIP_AUTH:
        return await _get_mock_user(db)

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无法验证凭据",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if not authorization:
        raise credentials_exception

    # 解析Bearer token
    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise credentials_exception
    except ValueError:
        raise credentials_exception

    # 解码token
    try:
        payload = decode_access_token(token)
        user_id: str = payload.get("sub")
        if not user_id:
            raise credentials_exception
    except Exception:
        raise credentials_exception

    # 查询用户
    from app.services.user_service import user_service
    user = await user_service.get_by_id(db, user_id)
    if not user:
        raise credentials_exception

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户已被禁用"
        )

    return user


async def _get_mock_user(db: AsyncSession) -> User:
    """
    获取模拟用户（开发模式使用）
    如果没有用户则创建一个默认用户
    """
    from sqlalchemy import select

    # 尝试获取第一个用户
    result = await db.execute(select(User).limit(1))
    user = result.scalar_one_or_none()

    if user:
        return user

    # 如果没有用户，创建一个默认用户
    from app.models.role import Role

    # 获取默认角色
    result = await db.execute(select(Role).where(Role.name == "REGULAR_USER"))
    role = result.scalar_one_or_none()

    if not role:
        # 如果没有角色，创建一个
        role = Role(name="REGULAR_USER", description="普通用户")
        db.add(role)
        await db.commit()
        await db.refresh(role)

    # 创建默认用户
    mock_user = User(
        wechat_id="test_user",
        name="测试用户",
        email="test@example.com",
        is_active=True,
        roles=[role]
    )
    db.add(mock_user)
    await db.commit()
    await db.refresh(mock_user)

    return mock_user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    获取当前活跃用户

    Args:
        current_user: 当前用户

    Returns:
        User: 活跃用户
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户已被禁用"
        )
    return current_user


# ===== 权限检查依赖 =====
def require_permission(permission: str):
    """
    要求特定权限的依赖

    Args:
        permission: 需要的权限字符串 (如 "document.upload")

    Returns:
        依赖函数
    """
    async def permission_checker(
        current_user: User = Depends(get_current_active_user)
    ) -> User:
        from app.core.permissions import check_user_permission

        if not check_user_permission(current_user, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"缺少权限: {permission}"
            )
        return current_user

    return permission_checker


async def require_admin(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """
    要求管理员权限

    Args:
        current_user: 当前用户

    Returns:
        User: 管理员用户
    """
    from app.core.permissions import is_admin

    if not is_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限"
        )
    return current_user


# ===== Milvus依赖 =====
async def get_milvus_client():
    """获取Milvus客户端"""
    from app.integrations.milvus_client import milvus_client
    return milvus_client


# ===== Meilisearch依赖 =====
async def get_meilisearch_client():
    """获取Meilisearch客户端"""
    from app.integrations.search_engine import meilisearch_client
    return meilisearch_client


# ===== LLM依赖 =====
async def get_llm_client():
    """获取LLM客户端"""
    from app.integrations.llm_server import llm_client
    return llm_client


# ===== RAG Pipeline依赖 =====
async def get_rag_pipeline():
    """获取RAG Pipeline实例"""
    from app.rag.pipeline import RAGPipeline
    from app.integrations.milvus_client import milvus_client
    from app.integrations.search_engine import meilisearch_client
    from app.integrations.llm_server import llm_client

    return RAGPipeline(
        vector_client=milvus_client,
        search_client=meilisearch_client,
        llm_client=llm_client
    )


# ===== 企业微信Bot依赖 =====
async def get_wechat_bot():
    """获取企业微信Bot客户端"""
    from app.integrations.wechat.bot import wechat_bot
    return wechat_bot
