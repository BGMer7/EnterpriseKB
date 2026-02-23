"""
对话相关Schema
"""
from typing import Optional, List
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field


# ===== 对话相关 =====
class ConversationBase(BaseModel):
    """对话基础Schema"""
    title: Optional[str] = None


class ConversationCreate(ConversationBase):
    """创建对话Schema"""
    pass


class ConversationResponse(ConversationBase):
    """对话响应Schema"""
    id: str
    user_id: str
    created_at: datetime
    updated_at: datetime
    message_count: int = 0

    class Config:
        from_attributes = True


# ===== 消息相关 =====
class MessageBase(BaseModel):
    """消息基础Schema"""
    content: str
    role: str = Field(..., pattern="^(user|assistant|system)$")


class MessageCreate(MessageBase):
    """创建消息Schema"""
    conversation_id: str


class MessageResponse(MessageBase):
    """消息响应Schema"""
    id: str
    conversation_id: str
    sources: List[dict] = []
    feedback: Optional[str] = None
    feedback_comment: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ===== 对话请求/响应 =====
class ChatRequest(BaseModel):
    """对话请求Schema"""
    query: str = Field(..., min_length=1, max_length=1000)
    conversation_id: Optional[str] = None
    stream: bool = False


class ChatResponse(BaseModel):
    """对话响应Schema"""
    conversation_id: str
    message_id: str
    answer: str
    sources: List[dict] = []
    suggested_questions: List[str] = []


class SourceReference(BaseModel):
    """来源引用Schema"""
    chunk_id: str
    document_id: str
    document_title: str
    section: Optional[str] = None
    page_number: Optional[int] = None
    content_preview: str
    score: float


# ===== 反馈相关 =====
class FeedbackRequest(BaseModel):
    """反馈请求Schema"""
    message_id: str
    feedback: str = Field(..., pattern="^(helpful|not_helpful|inaccurate)$")
    comment: Optional[str] = None


# ===== 多轮对话上下文 =====
class ConversationContext(BaseModel):
    """对话上下文Schema"""
    conversation_id: str
    messages: List[dict] = []


# ===== 流式响应 =====
class StreamChunk(BaseModel):
    """流式响应块Schema"""
    type: str  # start, chunk, end, error
    data: Optional[dict] = None
    delta: Optional[str] = None  # 流式增量文本
