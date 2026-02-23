"""
管理后台相关Schema
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


# ===== 通用响应 =====
class ApiResponse(BaseModel):
    """通用API响应Schema"""
    success: bool = True
    message: Optional[str] = None
    data: Optional[Any] = None


class ErrorResponse(BaseModel):
    """错误响应Schema"""
    success: bool = False
    error: Dict[str, Any] = {}


# ===== 统计数据 =====
class DashboardStats(BaseModel):
    """仪表盘统计数据Schema"""
    total_users: int
    total_documents: int
    total_conversations: int
    total_queries: int
    today_queries: int
    avg_response_time: float  # 秒


class QueryStats(BaseModel):
    """查询统计Schema"""
    date: str
    count: int


class TopQuestion(BaseModel):
    """热门问题Schema"""
    question: str
    count: int


class UnansweredQuestion(BaseModel):
    """无答案问题Schema"""
    question: str
    count: int
    last_seen: datetime


class StatsResponse(BaseModel):
    """统计响应Schema"""
    overview: DashboardStats
    query_trend: List[QueryStats]
    top_questions: List[TopQuestion]
    unanswered_questions: List[UnansweredQuestion]


# ===== 系统配置 =====
class SystemConfig(BaseModel):
    """系统配置Schema"""
    key: str
    value: Any
    description: Optional[str] = None


class SystemConfigUpdate(BaseModel):
    """系统配置更新Schema"""
    value: Any


# ===== 审计日志 =====
class AuditLogFilter(BaseModel):
    """审计日志过滤Schema"""
    user_id: Optional[str] = None
    action: Optional[str] = None
    resource_type: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    page: int = 1
    page_size: int = 20


class AuditLogResponse(BaseModel):
    """审计日志响应Schema"""
    id: str
    user_id: Optional[str] = None
    action: str
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    request_data: Optional[dict] = None
    response_status: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True


class AuditLogListResponse(BaseModel):
    """审计日志列表响应Schema"""
    logs: List[AuditLogResponse]
    total: int
    page: int
    page_size: int
