"""
审计日志数据模型
"""
from typing import Optional
from uuid import UUID, uuid4
from datetime import datetime

from sqlalchemy import String, ForeignKey, Integer, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class AuditLog(Base, TimestampMixin):
    """审计日志模型"""
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=uuid4
    )
    user_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("users.id"),
        nullable=True,
        index=True
    )
    action: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True
    )
    resource_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    resource_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        nullable=True
    )
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    request_data: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True
    )
    response_status: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    def __repr__(self) -> str:
        return f"<AuditLog {self.action} by {self.user_id}>"
