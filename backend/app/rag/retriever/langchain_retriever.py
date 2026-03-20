"""
LangChain-based Retriever
使用 LangChain 框架的 Milvus 集成
"""
from typing import List, Optional
import logging

from app.rag.retriever.base import BaseRetriever, RetrievalResult
from app.config import settings

logger = logging.getLogger(__name__)


class LangChainRetriever(BaseRetriever):
    """
    LangChain 实现 of BaseRetriever
    使用 LangChain 的 Milvus vectorstore 进行检索
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
        self._vectorstore = None

    def _get_vectorstore(self):
        """
        Lazy-load LangChain Milvus vectorstore

        Returns:
            LangChain Milvus vectorstore instance
        """
        if self._vectorstore is None:
            try:
                from langchain_milvus import Milvus
                from langchain_openai import OpenAIEmbeddings
            except ImportError as e:
                raise ImportError(
                    "LangChain is not installed. "
                    "Install with: pip install langchain langchain-milvus langchain-openai"
                ) from e

            from app.integrations.milvus_client import get_milvus_client
            milvus_client = get_milvus_client()

            # 构建 OpenAI-compatible embedding 接口
            # 复用现有的 BGE-M3 embedding 服务
            embeddings = OpenAIEmbeddings(
                model=self.embedding_model,
                openai_api_base=settings.LLM_API_URL,  # vLLM API 地址
                openai_api_key="dummy",  # LangChain 需要此参数
            )

            # 确定 URI
            if milvus_client._is_cloud:
                uri = milvus_client.cloud_uri
                token = milvus_client.cloud_password
            else:
                uri = f"http://{milvus_client.host}:{milvus_client.port}"
                token = None

            self._vectorstore = Milvus(
                embedding_function=embeddings,
                connection_args={
                    "uri": uri,
                    "token": token,
                },
                collection_name=self.collection_name,
            )

        return self._vectorstore

    async def retrieve(
        self,
        query: str,
        top_k: int = 30,
        filter_expression: Optional[str] = None
    ) -> List[RetrievalResult]:
        """
        使用 LangChain 进行相似度检索

        Args:
            query: 查询文本
            top_k: 返回结果数量
            filter_expression: 过滤表达式

        Returns:
            List[RetrievalResult]: 检索结果列表
        """
        vectorstore = self._get_vectorstore()

        # LangChain 的 similarity_search 是同步的，使用 asyncio.to_thread
        import asyncio
        docs = await asyncio.to_thread(
            vectorstore.similarity_search,
            query=query,
            k=top_k or self.top_k,
            filter=filter_expression
        )

        # 转换为 RetrievalResult
        results = []
        for doc in docs:
            results.append(RetrievalResult(
                id=doc.metadata.get("chunk_id", ""),
                chunk_id=doc.metadata.get("chunk_id", ""),
                document_id=doc.metadata.get("document_id", ""),
                content=doc.page_content,
                title=doc.metadata.get("title", ""),
                score=1.0,  # LangChain similarity_search 不返回分数
                metadata=doc.metadata,
                department_id=doc.metadata.get("department_id"),
                is_public=doc.metadata.get("is_public"),
                allowed_roles=doc.metadata.get("allowed_roles", []),
                page_number=doc.metadata.get("page_number"),
                section=doc.metadata.get("section"),
                chunk_index=doc.metadata.get("chunk_index"),
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
