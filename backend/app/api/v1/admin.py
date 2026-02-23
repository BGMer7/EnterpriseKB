"""
管理后台相关API
"""
from typing import Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies import require_admin
from app.schemas.admin import (
    StatsResponse, SystemConfig, SystemConfigUpdate,
    AuditLogFilter, AuditLogListResponse
)
from app.models.user import User
from app.core.constants import AuditAction

router = APIRouter()


@router.get("/dashboard/stats", response_model=StatsResponse)
async def get_dashboard_stats(
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    获取仪表盘统计数据
    """
    from app.services.audit_service import audit_service

    # 默认查询最近7天
    if not end_date:
        end_date = datetime.utcnow()
    if not start_date:
        start_date = end_date - timedelta(days=7)

    return await audit_service.get_dashboard_stats(
        db=db,
        start_date=start_date,
        end_date=end_date
    )


@router.get("/audit-logs", response_model=AuditLogListResponse)
async def get_audit_logs(
    filter: AuditLogFilter = Depends(),
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    获取审计日志
    """
    from app.services.audit_service import audit_service

    return await audit_service.list_audit_logs(
        db=db,
        user_id=filter.user_id,
        action=filter.action,
        resource_type=filter.resource_type,
        start_date=filter.start_date,
        end_date=filter.end_date,
        page=filter.page,
        page_size=filter.page_size
    )


@router.get("/system/config", response_model=list[SystemConfig])
async def get_system_config(
    current_user: User = Depends(require_admin)
):
    """
    获取系统配置
    """
    from app.services.audit_service import audit_service

    return await audit_service.get_system_config()


@router.put("/system/config/{config_key}")
async def update_system_config(
    config_key: str,
    request: SystemConfigUpdate,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    更新系统配置
    """
    from app.services.audit_service import audit_service

    await audit_service.update_system_config(
        db=db,
        key=config_key,
        value=request.value,
        user_id=str(current_user.id)
    )

    return {"message": "配置更新成功"}


@router.get("/health")
async def system_health_check():
    """
    系统健康检查
    检查所有服务的健康状态
    """
    health_status = {
        "status": "healthy",
        "services": {}
    }

    # 检查数据库
    try:
        from app.db.session import engine
        async with engine.begin() as conn:
            await conn.execute("SELECT 1")
        health_status["services"]["database"] = "healthy"
    except Exception as e:
        health_status["services"]["database"] = f"unhealthy: {str(e)}"
        health_status["status"] = "unhealthy"

    # 检查Redis
    try:
        from app.utils.cache import redis_client
        await redis_client.ping()
        health_status["services"]["redis"] = "healthy"
    except Exception as e:
        health_status["services"]["redis"] = f"unhealthy: {str(e)}"
        health_status["status"] = "degraded"

    # 检查Milvus
    try:
        from app.integrations.milvus_client import milvus_client
        health_status["services"]["milvus"] = milvus_client.check_health()
    except Exception as e:
        health_status["services"]["milvus"] = f"unhealthy: {str(e)}"
        health_status["status"] = "degraded"

    # 检查Meilisearch
    try:
        from app.integrations.search_engine import meilisearch_client
        health_status["services"]["meilisearch"] = await meilisearch_client.check_health()
    except Exception as e:
        health_status["services"]["meilisearch"] = f"unhealthy: {str(e)}"
        health_status["status"] = "degraded"

    # 检查LLM
    try:
        from app.integrations.llm_server import llm_client
        health_status["services"]["llm"] = await llm_client.check_health()
    except Exception as e:
        health_status["services"]["llm"] = f"unhealthy: {str(e)}"
        health_status["status"] = "degraded"

    return health_status
