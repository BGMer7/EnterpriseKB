"""
角色数据模型
"""
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class Role(Base, TimestampMixin):
    """角色模型"""
    __tablename__ = "roles"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=uuid4
    )
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    permissions: Mapped[list[str]] = mapped_column(
        String(2000),  # JSON数组
        nullable=False,
        default="[]"
    )

    def __repr__(self) -> str:
        return f"<Role {self.name}>"
