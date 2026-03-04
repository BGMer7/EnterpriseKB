"""
文档服务
实现文档上传、处理、CRUD操作
"""
import logging
import hashlib
from typing import List, Optional, Dict, Any
from pathlib import Path
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.constants import DocumentStatus
from app.db.session import get_db_session
from app.models.document import Document, Chunk
from app.models.qa_pair import QAPair
from app.models.audit_log import AuditLog
from app.schemas.document import DocumentResponse
from app.integrations.minio_client import get_minio_client
from app.processors.parser import parse_document
from app.processors.cleaner import clean_document
from app.processors.chunker import chunk_document
from app.processors.multimodal_chunker import multimodal_chunk_document, has_multimodal_content
from app.rag.embedding import encode_text
from app.rag.pipeline import RAGPipeline
from app.integrations.milvus_client import get_milvus_client
from app.integrations.search_engine import get_meilisearch_client
from app.config import settings

logger = logging.getLogger(__name__)


class DocumentService:
    """文档服务"""

    async def upload_document(
        self,
        db: AsyncSession,
        file,
        user_id: str,
        title: Optional[str] = None,
        department_id: Optional[str] = None,
        is_public: bool = False,
        allowed_roles: List[str] = None
    ) -> Dict[str, Any]:
        """
        上传文档

        Args:
            db: 数据库会话
            file: 文件对象
            user_id: 上传用户ID
            title: 文档标题
            department_id: 部门ID
            is_public: 是否公开
            allowed_roles: 允许的角色列表

        Returns:
            Dict: 上传结果
        """
        # 1. 验证文件
        if file.size > settings.MAX_FILE_SIZE:
            raise ValueError(f"File size exceeds limit of {settings.MAX_FILE_SIZE / 1024 / 1024}MB")

        file_type = file.filename.split('.')[-1].lower()
        if file_type not in settings.ALLOWED_FILE_TYPES:
            raise ValueError(f"Unsupported file type: {file_type}")

        # 2. 计算文件哈希
        file_content = await file.read()
        file_hash = hashlib.sha256(file_content).hexdigest()

        # 3. 检查重复
        existing = await db.execute(
            select(Document).where(Document.file_hash == file_hash)
        )
        if existing.scalar_one_or_none():
            return {
                "document_id": str(existing.scalar_one_or_none().id),
                "status": "exists",
                "message": "Document already exists"
            }

        # 4. 保存到MinIO
        minio_client = get_minio_client()
        object_name = f"docs/{file_hash}{Path(file.filename).suffix}"

        await minio_client.upload_file(
            object_name=object_name,
            content=file_content,
            content_type=file.content_type
        )

        # 5. 解析文档
        document_id = str(__import__('uuid').uuid4())
        temp_file = f"/tmp/{document_id}_{file.filename}"
        Path(temp_file).parent.mkdir(parents=True, exist_ok=True)

        try:
            # 保存临时文件
            with open(temp_file, 'wb') as f:
                f.write(file_content)

            # 解析文档
            parse_result = parse_document(temp_file, file_type)

            # 6. 创建文档记录
            doc_title = title or Path(file.filename).stem

            document = Document(
                id=document_id,
                title=doc_title,
                file_name=file.filename,
                file_type=file_type,
                file_path=object_name,
                file_hash=file_hash,
                file_size=file.size,
                department_id=department_id,
                uploaded_by=user_id,
                is_public=is_public,
                allowed_roles=allowed_roles or [],
                status=DocumentStatus.DRAFT,
                version=1,
                page_count=parse_result["metadata"].get("page_count", 1)
            )

            db.add(document)
            await db.commit()

            logger.info(f"Document {document_id} uploaded successfully")

            # TODO: 异步处理文档（分块、向量化、入库）
            # 这里同步处理，生产环境应使用异步任务
            await self._process_document(
                db=db,
                document_id=document_id,
                parse_result=parse_result
            )

            return {
                "document_id": document_id,
                "status": "success",
                "message": "Document uploaded and processed successfully"
            }

        finally:
            # 清理临时文件
            if Path(temp_file).exists():
                Path(temp_file).unlink()

    async def _process_document(
        self,
        db: AsyncSession,
        document_id: str,
        parse_result: Dict[str, Any]
    ):
        """
        处理文档：分块、向量化、入库

        Args:
            db: 数据库会话
            document_id: 文档ID
            parse_result: 解析结果
        """
        # 1. 数据清洗
        content = parse_result["content"]
        cleaned_content = clean_document(
            content,
            options={
                "remove_page_numbers": True,
                "remove_headers": True,
                "normalize_whitespace": True
            }
        )

        # 2. 文档分块
        # 检查是否包含多模态内容
        pages = parse_result.get("pages", [])
        if has_multimodal_content(pages):
            # 使用多模态分块
            logger.info(f"Using multimodal chunking for document {document_id}")
            chunks = multimodal_chunk_document(
                document_id=document_id,
                pages=pages,
                strategy="multimodal"
            )
        else:
            # 使用传统分块
            chunks = chunk_document(
                document_id=document_id,
                content=cleaned_content,
                pages=pages,
                strategy="fixed"
            )

        if not chunks:
            logger.warning(f"No chunks generated for document {document_id}")
            return

        # 3. 向量化
        chunk_texts = [c["content"] for c in chunks]
        embeddings = encode_text(chunk_texts)

        # 4. 保存到SQLite
        for chunk_data in chunks:
            # 构建扩展metadata
            metadata = chunk_data.get("metadata", {})

            # 添加多模态元数据
            if "chunk_type" in chunk_data:
                metadata["chunk_type"] = chunk_data["chunk_type"]
            if chunk_data.get("images"):
                metadata["images"] = chunk_data["images"]
            if chunk_data.get("tables"):
                metadata["tables"] = chunk_data["tables"]

            chunk = Chunk(
                document_id=document_id,
                chunk_index=chunk_data["chunk_index"],
                content=chunk_data["content"],
                metadata=metadata
            )
            db.add(chunk)

        await db.commit()

        # 5. 插入到向量数据库
        milvus_client = get_milvus_client()
        milvus_data = []

        for idx, (chunk_data, embedding) in enumerate(zip(chunks, embeddings.tolist())):
            # 构建扩展metadata
            metadata = chunk_data.get("metadata", {})
            chunk_type = chunk_data.get("chunk_type", "text")

            milvus_data.append({
                "chunk_id": chunk_data["id"],
                "document_id": document_id,
                "content": chunk_data["content"],
                "title": parse_result.get("filename", "Unknown"),
                "department_id": None,  # 从document表获取
                "is_public": False,  # 从document表获取
                "allowed_roles": [],  # 从document表获取
                "page_number": chunk_data.get("page_number") or metadata.get("page_number"),
                "section": chunk_data.get("section") or metadata.get("section"),
                "chunk_index": chunk_data["chunk_index"],
                "chunk_type": chunk_type,
                "has_images": len(chunk_data.get("images", [])) > 0,
                "has_tables": len(chunk_data.get("tables", [])) > 0,
                "embedding": embedding,
                "created_at": int(datetime.utcnow().timestamp()),
            })

        milvus_ids = milvus_client.insert_chunks(milvus_data)

        # 更新chunk的milvus_id
        for chunk, milvus_id in zip(chunks, milvus_ids):
            chunk_obj = await db.get(Chunk, chunk["id"])
            if chunk_obj:
                chunk_obj.milvus_id = milvus_id

        await db.commit()

        # 6. 插入到全文搜索
        meilisearch_client = get_meilisearch_client()

        search_data = []
        for chunk_data in chunks:
            search_data.append({
                "chunk_id": chunk_data["id"],
                "document_id": document_id,
                "content": chunk_data["content"],
                "title": parse_result.get("filename", "Unknown"),
                "department_id": None,
                "is_public": False,
                "allowed_roles": [],
                "page_number": chunk_data["metadata"].get("page_number"),
                "section": chunk_data["metadata"].get("section"),
                "chunk_index": chunk_data["chunk_index"],
                "created_at": int(datetime.utcnow().timestamp()),
            })

        meilisearch_client.add_documents(search_data)

        logger.info(f"Document {document_id} processed: {len(chunks)} chunks")

    async def list_documents(
        self,
        db: AsyncSession,
        user,
        page: int = 1,
        page_size: int = 20,
        status: Optional[str] = None,
        department_id: Optional[str] = None,
        search: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        获取文档列表

        Args:
            db: 数据库会话
            user: 用户对象
            page: 页码
            page_size: 每页数量
            status: 状态过滤
            department_id: 部门过滤
            search: 搜索关键词

        Returns:
            Dict: 文档列表
        """
        query = select(Document)

        # 应用权限过滤
        # 用户可以查看：公开文档、自己上传的、同部门文档、有权限的文档
        from app.core.permissions import can_view_document

        query = query.where(
            Document.id.in_(
                select(Document.id)
                .where(
                    (Document.is_public == True) |
                    (Document.uploaded_by == str(user.id)) |
                    (Document.department_id == user.department_id) |
                    (Document.id.in_(
                        select(Document.id)
                        .where(Document.status == DocumentStatus.PUBLISHED)
                    ))
                )
            )
        )

        # 状态过滤
        if status:
            query = query.where(Document.status == status)

        # 部门过滤
        if department_id:
            query = query.where(Document.department_id == department_id)

        # 搜索过滤
        if search:
            query = query.where(Document.title.ilike(f"%{search}%"))

        # 分页
        query = query.order_by(Document.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await db.execute(query)
        documents = result.scalars().all()

        # 计算总数
        count_query = select(func.count()).select_from(query.subquery().limit(None))
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        return {
            "documents": [DocumentResponse.model_validate(d) for d in documents],
            "total": total,
            "page": page,
            "page_size": page_size
        }

    async def get_document(
        self,
        db: AsyncSession,
        document_id: str,
        user
    ) -> Document:
        """
        获取文档详情

        Args:
            db: 数据库会话
            document_id: 文档ID
            user: 用户对象

        Returns:
            Document: 文档对象
        """
        result = await db.execute(
            select(Document).where(Document.id == document_id)
        )
        document = result.scalar_one_or_none()

        if not document:
            raise ValueError(f"Document {document_id} not found")

        # 权限检查
        from app.core.permissions import can_view_document
        if not can_view_document(user, document):
            raise PermissionError("You don't have permission to view this document")

        return document

    async def update_document(
        self,
        db: AsyncSession,
        document_id: str,
        user,
        update_data: Dict[str, Any]
    ) -> Document:
        """
        更新文档

        Args:
            db: 数据库会话
            document_id: 文档ID
            user: 用户对象
            update_data: 更新数据

        Returns:
            Document: 更新后的文档对象
        """
        result = await db.execute(
            select(Document).where(Document.id == document_id)
        )
        document = result.scalar_one_or_none()

        if not document:
            raise ValueError(f"Document {document_id} not found")

        # 权限检查
        from app.core.permissions import can_edit_document
        if not can_edit_document(user, document):
            raise PermissionError("You don't have permission to edit this document")

        # 更新字段
        for key, value in update_data.items():
            if hasattr(document, key):
                setattr(document, key, value)

        await db.commit()
        await db.refresh(document)

        return document

    async def delete_document(
        self,
        db: AsyncSession,
        document_id: str,
        user
    ):
        """
        删除文档

        Args:
            db: 数据库会话
            document_id: 文档ID
            user: 用户对象
        """
        result = await db.execute(
            select(Document).where(Document.id == document_id)
        )
        document = result.scalar_one_or_none()

        if not document:
            raise ValueError(f"Document {document_id} not found")

        # 权限检查
        from app.core.permissions import can_delete_document
        if not can_delete_document(user, document):
            raise PermissionError("You don't have permission to delete this document")

        # 从向量数据库和全文搜索删除
        milvus_client = get_milvus_client()
        milvus_client.delete_by_document(document_id)

        meilisearch_client = get_meilisearch_client()
        meilisearch_client.delete_by_document(document_id)

        # 删除数据库记录（会级联删除chunks）
        await db.delete(document)
        await db.commit()

        logger.info(f"Document {document_id} deleted")

    async def get_document_chunks(
        self,
        db: AsyncSession,
        document_id: str,
        user
    ) -> List[Chunk]:
        """
        获取文档的分块列表

        Args:
            db: 数据库会话
            document_id: 文档ID
            user: 用户对象

        Returns:
            List[Chunk]: 分块列表
        """
        # 权限检查（复用get_document）
        await self.get_document(db, document_id, user)

        # 获取chunks
        result = await db.execute(
            select(Chunk)
            .where(Chunk.document_id == document_id)
            .order_by(Chunk.chunk_index)
        )
        chunks = result.scalars().all()

        return chunks

    async def publish_document(
        self,
        db: AsyncSession,
        document_id: str,
        user_id: str
    ):
        """
        发布文档

        Args:
            db: 数据库会话
            document_id: 文档ID
            user_id: 用户ID
        """
        result = await db.execute(
            select(Document).where(Document.id == document_id)
        )
        document = result.scalar_one_or_none()

        if not document:
            raise ValueError(f"Document {document_id} not found")

        document.status = DocumentStatus.PUBLISHED
        document.reviewed_by = user_id
        document.published_at = datetime.utcnow()

        await db.commit()
        await db.refresh(document)

        logger.info(f"Document {document_id} published by {user_id}")

    async def reject_document(
        self,
        db: AsyncSession,
        document_id: str,
        user_id: str,
        comment: Optional[str] = None
    ):
        """
        拒绝文档

        Args:
            db: 数据库会话
            document_id: 文档ID
            user_id: 用户ID
            comment: 拒绝原因
        """
        result = await db.execute(
            select(Document).where(Document.id == document_id)
        )
        document = result.scalar_one_or_none()

        if not document:
            raise ValueError(f"Document {document_id} not found")

        document.status = DocumentStatus.REJECTED
        document.reviewed_by = user_id
        document.review_comment = comment

        await db.commit()
        await db.refresh(document)

        logger.info(f"Document {document_id} rejected by {user_id}: {comment}")


# 全局文档服务实例
document_service = DocumentService()


def get_document_service() -> DocumentService:
    """获取文档服务单例"""
    return document_service
