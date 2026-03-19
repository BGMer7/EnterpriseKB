"""
用户数据模型
"""
from typing import Optional, TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import String, ForeignKey, Boolean, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.department import Department
    from app.models.role import Role
    from app.models.conversation import Conversation
    from app.models.document import Document


class User(Base, TimestampMixin):
    """用户模型"""
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(
        String(36),
        primary_key=True,
        default=uuid4
    )
    wechat_id: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        nullable=False,
        index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    password_hash: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True
    )
    avatar_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # 外键
    department_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("departments.id"),
        nullable=True,
        index=True
    )

    # 关系
    department: Mapped[Optional["Department"]] = relationship(
        "Department",
        back_populates="users"
    )
    roles: Mapped[list["Role"]] = relationship(
        "Role",
        secondary="user_roles",
        backref="users",
        foreign_keys="UserRole.user_id"
    )
    conversations: Mapped[list["Conversation"]] = relationship(
        "Conversation",
        back_populates="user"
    )
    uploaded_documents: Mapped[list["Document"]] = relationship(
        "Document",
        foreign_keys="Document.uploaded_by",
        back_populates="uploader"
    )
    last_login_at: Mapped[Optional[DateTime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    def __repr__(self) -> str:
        return f"<User {self.name} ({self.wechat_id})>"

    def has_role(self, role_name: str) -> bool:
        """检查用户是否有指定角色"""
        return any(role.name == role_name for role in self.roles)

    def has_permission(self, permission: str) -> bool:
        """检查用户是否有指定权限"""
        from app.core.permissions import get_user_permissions
        user_permissions = get_user_permissions(self)
        return permission in user_permissions
