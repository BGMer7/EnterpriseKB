"""
LlamaIndex-based Retriever
使用 LlamaIndex 框架的 Milvus 向量存储
"""
from typing import List, Optional
import logging

from app.rag.retriever.base import BaseRetriever, RetrievalResult
from app.config import settings

logger = logging.getLogger(__name__)


class LlamaIndexRetriever(BaseRetriever):
    """
    LlamaIndex 实现 of BaseRetriever
    使用 LlamaIndex 的 MilvusVectorStore 进行检索
    """

    def __init__(
        self,
        collection_name: str = settings.MILVUS_COLLECTION_NAME,
        embedding_model: str = settings.EMBEDDING_MODEL,
        top_k: int = 30
    ):
        self.collection_name = collection_name
        self.embedding_model = embedding_model
        self.top_k = top_k
        self._vector_store = None
        self._index = None

    def _get_vector_store(self):
        """
        Lazy-load LlamaIndex MilvusVectorStore

        Returns:
            LlamaIndex MilvusVectorStore instance
        """
        if self._vector_store is None:
            try:
                from llama_index.vector_stores.milvus import MilvusVectorStore
                from llama_index.core import VectorStoreIndex
            except ImportError as e:
                raise ImportError(
                    "LlamaIndex is not installed. "
                    "Install with: pip install llama-index llama-index-vector-stores-milvus"
                ) from e

            # 确定 URI
            if settings.MILVUS_CLOUD_URI:
                uri = settings.MILVUS_CLOUD_URI
                token = settings.MILVUS_CLOUD_PASSWORD
            else:
                uri = f"http://{settings.MILVUS_HOST}:{settings.MILVUS_PORT}"
                token = None

            self._vector_store = MilvusVectorStore(
                collection_name=self.collection_name,
                uri=uri,
                token=token,
                dimension=settings.MILVUS_DIMENSION,
                overwrite=False,  # 不覆盖已有数据
            )

        return self._vector_store

    def _get_index(self):
        """Get or create the index"""
        if self._index is None:
            from llama_index.core import VectorStoreIndex
            vector_store = self._get_vector_store()
            self._index = VectorStoreIndex.from_vector_store(vector_store)
        return self._index

    async def retrieve(
        self,
        query: str,
        top_k: int = 30,
        filter_expression: Optional[str] = None
    ) -> List[RetrievalResult]:
        """
        使用 LlamaIndex 进行检索

        Args:
            query: 查询文本
            top_k: 返回结果数量
            filter_expression: 过滤表达式

        Returns:
            List[RetrievalResult]: 检索结果列表
        """
        index = self._get_index()

        # 构建 retriever
        retriever = index.as_retriever(
            similarity_top_k=top_k or self.top_k
        )

        # LlamaIndex 的 retrieve 是异步的
        import asyncio
        nodes = await asyncio.to_thread(retriever.retrieve, query)

        # 转换为 RetrievalResult
        results = []
        for node in nodes:
            results.append(RetrievalResult(
                id=node.metadata.get("chunk_id", ""),
                chunk_id=node.metadata.get("chunk_id", ""),
                document_id=node.metadata.get("document_id", ""),
                content=node.text,
                title=node.metadata.get("title", ""),
                score=node.score or 0.0,
                metadata=node.metadata,
                department_id=node.metadata.get("department_id"),
                is_public=node.metadata.get("is_public"),
                allowed_roles=node.metadata.get("allowed_roles", []),
                page_number=node.metadata.get("page_number"),
                section=node.metadata.get("section"),
                chunk_index=node.metadata.get("chunk_index"),
            ))

        return results

    async def retrieve_with_context(
        self,
        query: str,
        top_k: int = 30,
        filter_expression: Optional[str] = None
    ) -> tuple[List[RetrievalResult], str]:
        """
        检索并返回格式化的上下文

        Args:
            query: 查询文本
            top_k: 返回结果数量
            filter_expression: 过滤表达式

        Returns:
            tuple: (检索结果列表, 格式化的上下文字符串)
        """
        results = await self.retrieve(query, top_k, filter_expression)

        # 格式化上下文
        context_parts = []
        for idx, result in enumerate(results, 1):
            context_parts.append(
                f"【文档{idx}】{result.title}\n"
                f"来源：{result.section or 'N/A'}\n"
                f"页码：{result.page_number or 'N/A'}\n"
                f"内容：{result.content}"
            )

        context = "\n\n".join(context_parts)
        return results, context
