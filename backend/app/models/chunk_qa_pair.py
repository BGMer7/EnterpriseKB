"""
文档块与QA对关联表
"""
from uuid import UUID, uuid4

from sqlalchemy import String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ChunkQAPair(Base):
    """文档块与QA对关联表"""
    __tablename__ = "chunk_qa_pairs"

    chunk_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("chunks.id", ondelete="CASCADE"),
        primary_key=True
    )
    qa_pair_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("qa_pairs.id", ondelete="CASCADE"),
        primary_key=True
    )

    def __repr__(self) -> str:
        return f"<ChunkQAPair {self.chunk_id} <-> {self.qa_pair_id}>"
