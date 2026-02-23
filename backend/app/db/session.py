"""
数据库会话管理
"""
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine
)

from app.config import settings

# 创建异步引擎
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    pool_timeout=settings.DATABASE_POOL_TIMEOUT,
    pool_recycle=settings.DATABASE_POOL_RECYCLE,
    pool_pre_ping=True,  # 检查连接是否可用
)

# 创建会话工厂
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,  # 提交后不过期，便于访问对象
    autocommit=False,
    autoflush=False,
)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    获取数据库会话

    Yields:
        AsyncSession: 数据库会话
    """
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db() -> None:
    """
    初始化数据库
    创建所有表（仅用于开发环境）
    """
    # 在生产环境应该使用Alembic迁移
    if settings.DEBUG:
        from app.db.base import Base
        from app.models import (
            user, role, permission, document,
            chunk, qa_pair, conversation, message
        )

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    print("Database initialized")


async def close_db() -> None:
    """
    关闭数据库连接
    """
    await engine.dispose()
    print("Database connection closed")
