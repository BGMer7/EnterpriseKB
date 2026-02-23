"""
部门数据模型
"""
from typing import Optional, TYPE_CHECKING
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.document import Document


class Department(Base, TimestampMixin):
    """部门模型"""
    __tablename__ = "departments"

    id: Mapped[UUID] = mapped_column(
        String(36),
        primary_key=True,
        default=uuid4
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    parent_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("departments.id"),
        nullable=True
    )

    # 关系
    users: Mapped[list["User"]] = relationship(
        "User",
        back_populates="department"
    )
    documents: Mapped[list["Document"]] = relationship(
        "Document",
        back_populates="department"
    )
    children: Mapped[list["Department"]] = relationship(
        "Department",
        backref="parent",
        remote_side="Department.id"
    )

    def __repr__(self) -> str:
        return f"<Department {self.code}: {self.name}>"
