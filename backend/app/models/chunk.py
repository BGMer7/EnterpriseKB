"""
文档块数据模型
"""
from typing import Optional, TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import String, Integer, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.document import Document
    from app.models.qa_pair import QAPair


class Chunk(Base, TimestampMixin):
    """文档块模型"""
    __tablename__ = "chunks"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=uuid4
    )
    document_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(String(10000), nullable=False)

    # 元数据 (避免使用 metadata 作为列名，这是 SQLAlchemy 保留字)
    chunk_metadata: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
        default={}
    )

    # 向量数据库ID
    milvus_id: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
        index=True
    )

    # 外键
    document_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("documents.id", ondelete="CASCADE"),
        primary_key=True
    )

    # 关系
    document: Mapped["Document"] = relationship(
        "Document",
        back_populates="chunks"
    )
    qa_pairs: Mapped[list["QAPair"]] = relationship(
        "QAPair",
        secondary="chunk_qa_pairs",
        backref="chunks"
    )

    def __repr__(self) -> str:
        return f"<Chunk {self.document_id}:{self.chunk_index}>"
