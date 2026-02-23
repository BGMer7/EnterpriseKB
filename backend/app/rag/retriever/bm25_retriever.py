"""
BM25检索器
使用Meilisearch进行全文检索
"""
from typing import List, Optional
import asyncio

from .base import BaseRetriever, RetrievalResult
from app.integrations.search_engine import get_meilisearch_client


class BM25Retriever(BaseRetriever):
    """
    Meilisearch BM25检索器
    """

    def __init__(self, top_k: int = 30):
        self.top_k = top_k

    async def retrieve(
        self,
        query: str,
        top_k: int = 30,
        filter_expression: Optional[str] = None
    ) -> List[RetrievalResult]:
        """
        BM25检索

        Args:
            query: 查询文本
            top_k: 返回结果数量
            filter_expression: 过滤表达式

        Returns:
            List[RetrievalResult]: 检索结果列表
        """
        # 获取Meilisearch客户端
        meilisearch_client = get_meilisearch_client()

        # 执行检索
        results = meilisearch_client.search(
            query=query,
            limit=top_k or self.top_k,
            filter_expression=filter_expression
        )

        # 转换为RetrievalResult
        retrieval_results = []
        for result in results:
            retrieval_results.append(RetrievalResult(
                id=result["id"],
                chunk_id=result["chunk_id"],
                document_id=result["document_id"],
                content=result["content"],
                title=result["title"],
                score=result["score"],
                metadata={
                    "page_number": result["page_number"],
                    "section": result["section"],
                    "chunk_index": result["chunk_index"],
                },
                department_id=result.get("department_id"),
                is_public=result.get("is_public"),
                allowed_roles=result.get("allowed_roles", []),
                page_number=result.get("page_number"),
                section=result.get("section"),
                chunk_index=result.get("chunk_index"),
            ))

        return retrieval_results

    def retrieve_with_permissions(
        self,
        query: str,
        department_id: Optional[str],
        roles: List[str],
        top_k: int = 30
    ) -> List[RetrievalResult]:
        """
        带权限的BM25检索

        Args:
            query: 查询文本
            department_id: 用户部门ID
            roles: 用户角色列表
            top_k: 返回结果数量

        Returns:
            List[RetrievalResult]: 检索结果列表
        """
        # 构建权限过滤表达式
        meilisearch_client = get_meilisearch_client()
        filter_expression = meilisearch_client.build_permission_filter(
            department_id=department_id,
            roles=roles
        )

        # 执行检索
        return asyncio.run(self.retrieve(
            query=query,
            top_k=top_k,
            filter_expression=filter_expression
        ))
