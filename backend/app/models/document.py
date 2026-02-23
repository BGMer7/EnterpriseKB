"""
文档数据模型
"""
from typing import Optional, TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import String, Integer, ForeignKey, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.department import Department
    from app.models.chunk import Chunk
    from app.models.qa_pair import QAPair


class Document(Base, TimestampMixin):
    """文档模型"""
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=uuid4
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_type: Mapped[str] = mapped_column(String(20), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    file_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    page_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    summary: Mapped[Optional[str]] = mapped_column(String(2000), nullable=True)

    # 权限相关
    is_public: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    allowed_roles: Mapped[list[str]] = mapped_column(
        String(500),  # JSON数组
        nullable=False,
        default="[]"
    )

    # 状态和版本
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="draft"  # draft, reviewing, published, rejected
    )
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    parent_doc_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("documents.id"),
        nullable=True
    )

    # 审核相关
    reviewed_by: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("users.id"),
        nullable=True
    )
    review_comment: Mapped[Optional[str]] = mapped_column(
        String(1000),
        nullable=True
    )

    # 外键
    uploaded_by: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id"),
        nullable=False,
        index=True
    )
    department_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("departments.id"),
        nullable=True,
        index=True
    )

    # 关系
    uploader: Mapped["User"] = relationship(
        "User",
        foreign_keys=[uploaded_by],
        back_populates="uploaded_documents"
    )
    department: Mapped[Optional["Department"]] = relationship(
        "Department",
        back_populates="documents"
    )
    reviewer: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[reviewed_by]
    )
    chunks: Mapped[list["Chunk"]] = relationship(
        "Chunk",
        back_populates="document",
        cascade="all, delete-orphan"
    )
    qa_pairs: Mapped[list["QAPair"]] = relationship(
        "QAPair",
        back_populates="document",
        cascade="all, delete-orphan"
    )
    parent: Mapped[Optional["Document"]] = relationship(
        "Document",
        remote_side="Document.id",
        backref="children"
    )

    def __repr__(self) -> str:
        return f"<Document {self.title} ({self.status})>"
