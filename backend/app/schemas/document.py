"""
文档相关Schema
"""
from typing import Optional, List
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field


# ===== 文档相关 =====
class DocumentBase(BaseModel):
    """文档基础Schema"""
    title: str = Field(..., min_length=1, max_length=500)


class DocumentCreate(DocumentBase):
    """创建文档Schema"""
    file_name: str
    file_type: str
    department_id: Optional[str] = None
    is_public: bool = False
    allowed_roles: List[str] = []


class DocumentUpdate(BaseModel):
    """更新文档Schema"""
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    is_public: Optional[bool] = None
    allowed_roles: Optional[List[str]] = None
    status: Optional[str] = None


class DocumentResponse(DocumentBase):
    """文档响应Schema"""
    id: str
    file_name: str
    file_type: str
    file_size: Optional[int] = None
    page_count: Optional[int] = None
    department_id: Optional[str] = None
    uploaded_by: str
    is_public: bool
    allowed_roles: List[str] = []
    status: str
    version: int
    parent_doc_id: Optional[str] = None
    summary: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    published_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class DocumentListResponse(BaseModel):
    """文档列表响应Schema"""
    documents: List[DocumentResponse]
    total: int
    page: int
    page_size: int


class DocumentUploadResponse(BaseModel):
    """文档上传响应Schema"""
    document_id: str
    status: str
    message: str


# ===== 文档块相关 =====
class ChunkBase(BaseModel):
    """文档块基础Schema"""
    content: str
    chunk_index: int


class ChunkResponse(ChunkBase):
    """文档块响应Schema"""
    id: str
    document_id: str
    metadata: dict = {}
    milvus_id: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ===== 文档搜索相关 =====
class SearchResult(BaseModel):
    """搜索结果Schema"""
    chunk_id: str
    document_id: str
    content: str
    title: str
    score: float
    metadata: dict = {}


class SearchResponse(BaseModel):
    """搜索响应Schema"""
    results: List[SearchResult]
    total: int
    query: str
