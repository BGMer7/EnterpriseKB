"""
QA对数据模型
"""
from typing import Optional, TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import String, Integer, ForeignKey, Boolean, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.document import Document
    from app.models.chunk import Chunk


class QAPair(Base, TimestampMixin):
    """QA对模型"""
    __tablename__ = "qa_pairs"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=uuid4
    )
    question: Mapped[str] = mapped_column(String(1000), nullable=False)
    answer: Mapped[str] = mapped_column(String(3000), nullable=False)

    # 状态
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending"  # pending, approved, rejected
    )

    # 使用统计
    usage_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # 外键
    created_by: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id"),
        nullable=False
    )
    document_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=True
    )

    # 关系
    creator: Mapped["User"] = relationship(
        "User",
        foreign_keys=[created_by]
    )
    document: Mapped[Optional["Document"]] = relationship(
        "Document",
        back_populates="qa_pairs"
    )
    chunks: Mapped[list["Chunk"]] = relationship(
        "Chunk",
        secondary="chunk_qa_pairs",
        backref="qa_pairs"
    )

    def __repr__(self) -> str:
        return f"<QAPair {self.question[:50]}...>"
