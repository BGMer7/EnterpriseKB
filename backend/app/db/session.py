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

# 根据数据库类型配置引擎参数
engine_kwargs = {
    "echo": settings.DEBUG,
}

# SQLite不需要连接池参数
if "sqlite" not in settings.DATABASE_URL:
    engine_kwargs.update({
        "pool_size": settings.DATABASE_POOL_SIZE,
        "max_overflow": settings.DATABASE_MAX_OVERFLOW,
        "pool_timeout": settings.DATABASE_POOL_TIMEOUT,
        "pool_recycle": settings.DATABASE_POOL_RECYCLE,
        "pool_pre_ping": True,
    })

# 创建异步引擎
engine = create_async_engine(
    settings.DATABASE_URL,
    **engine_kwargs
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


# 别名，保持与auth.py等文件的兼容性
get_db = get_db_session


async def init_db() -> None:
    """
    初始化数据库
    创建所有表（仅用于开发环境）
    """
    # 在生产环境应该使用Alembic迁移
    if settings.DEBUG:
        try:
            from app.db.base import Base
            from app.models import (
                user, role, document,
                chunk, qa_pair, conversation, message
            )

            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
        except Exception as e:
            print(f"Warning: Database initialization skipped: {e}")
            return

    print("Database initialized")


async def close_db() -> None:
    """
    关闭数据库连接
    """
    await engine.dispose()
    print("Database connection closed")
