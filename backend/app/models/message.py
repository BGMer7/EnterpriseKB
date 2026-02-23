"""
消息数据模型
"""
from typing import Optional, TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import String, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.conversation import Conversation


class Message(Base, TimestampMixin):
    """消息模型"""
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=uuid4
    )
    conversation_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    role: Mapped[str] = mapped_column(
        String(20),
        nullable=False
    )  # user, assistant, system
    content: Mapped[str] = mapped_column(String(10000), nullable=False)

    # 引用来源
    sources: Mapped[list[dict]] = mapped_column(
        JSON,
        nullable=False,
        default=[]
    )

    # 反馈
    feedback: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True
    )  # helpful, not_helpful, inaccurate
    feedback_comment: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True
    )

    # 元数据
    metadata: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
        default={}
    )

    # 关系
    conversation: Mapped["Conversation"] = relationship(
        "Conversation",
        back_populates="messages"
    )

    def __repr__(self) -> str:
        return f"<Message {self.role}: {self.content[:50]}...>"
