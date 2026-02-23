"""
混合检索器
结合向量检索和BM25检索，使用RRF融合结果
"""
from typing import List, Optional, Dict, Any
import asyncio
from concurrent.futures import ThreadPoolExecutor

from .base import BaseRetriever, RetrievalResult
from .vector_retriever import VectorRetriever
from .bm25_retriever import BM25Retriever
from app.integrations.milvus_client import get_milvus_client
from app.integrations.search_engine import get_meilisearch_client


class HybridRetriever(BaseRetriever):
    """
    混合检索器
    结合向量检索和BM25检索
    """

    def __init__(
        self,
        vector_top_k: int = 30,
        bm25_top_k: int = 30,
        fusion_k: int = 60,
        alpha: float = 0.5  # 向量检索权重
    ):
        self.vector_top_k = vector_top_k
        self.bm25_top_k = bm25_top_k
        self.fusion_k = fusion_k
        self.alpha = alpha

        self.vector_retriever = VectorRetriever(top_k=vector_top_k)
        self.bm25_retriever = BM25Retriever(top_k=bm25_top_k)

    async def retrieve(
        self,
        query: str,
        top_k: int = 30,
        filter_expression: Optional[str] = None
    ) -> List[RetrievalResult]:
        """
        混合检索

        Args:
            query: 查询文本
            top_k: 返回结果数量
            filter_expression: 过滤表达式

        Returns:
            List[RetrievalResult]: 融合后的检索结果列表
        """
        # 并行执行向量检索和BM25检索
        vector_results, bm25_results = await asyncio.gather(
            self.vector_retriever.retrieve(
                query=query,
                top_k=self.vector_top_k,
                filter_expression=filter_expression
            ),
            self.bm25_retriever.retrieve(
                query=query,
                top_k=self.bm25_top_k,
                filter_expression=filter_expression
            )
        )

        # RRF融合
        fused_results = self.reciprocal_rank_fusion(
            [vector_results, bm25_results],
            k=self.fusion_k
        )

        # 返回top_k
        return fused_results[:top_k]

    def retrieve_with_permissions(
        self,
        query: str,
        department_id: Optional[str],
        roles: List[str],
        top_k: int = 30
    ) -> List[RetrievalResult]:
        """
        带权限的混合检索

        Args:
            query: 查询文本
            department_id: 用户部门ID
            roles: 用户角色列表
            top_k: 返回结果数量

        Returns:
            List[RetrievalResult]: 检索结果列表
        """
        # 构建权限过滤表达式
        milvus_client = get_milvus_client()
        meilisearch_client = get_meilisearch_client()

        vector_filter = milvus_client.build_permission_filter(
            department_id=department_id,
            roles=roles
        )
        bm25_filter = meilisearch_client.build_permission_filter(
            department_id=department_id,
            roles=roles
        )

        # 并行执行带权限过滤的检索
        vector_results, bm25_results = asyncio.gather(
            self.vector_retriever.retrieve(
                query=query,
                top_k=self.vector_top_k,
                filter_expression=vector_filter
            ),
            self.bm25_retriever.retrieve(
                query=query,
                top_k=self.bm25_top_k,
                filter_expression=bm25_filter
            )
        )

        # RRF融合
        fused_results = self.reciprocal_rank_fusion(
            [vector_results, bm25_results],
            k=self.fusion_k
        )

        return fused_results[:top_k]

    def reciprocal_rank_fusion(
        self,
        results_list: List[List[RetrievalResult]],
        k: int = 60
    ) -> List[RetrievalResult]:
        """
        倒数排名融合 (RRF)

        Args:
            results_list: 多个检索结果列表
            k: RRF参数

        Returns:
            List[RetrievalResult]: 融合后的结果列表
        """
        # 使用chunk_id作为键
        score_map: Dict[str, Dict[str, Any]] = {}

        for results in results_list:
            for rank, result in enumerate(results, 1):
                chunk_id = result.chunk_id

                if chunk_id not in score_map:
                    score_map[chunk_id] = {
                        "result": result,
                        "score": 0,
                        "ranks": []
                    }

                # 计算RRF分数: 1 / (k + rank)
                rrf_score = 1 / (k + rank)
                score_map[chunk_id]["score"] += rrf_score
                score_map[chunk_id]["ranks"].append(rank)

        # 按融合分数排序
        sorted_results = sorted(
            score_map.values(),
            key=lambda x: x["score"],
            reverse=True
        )

        # 更新结果分数为融合分数
        for item in sorted_results:
            item["result"].score = item["score"]

        return [item["result"] for item in sorted_results]

    def weighted_fusion(
        self,
        vector_results: List[RetrievalResult],
        bm25_results: List[RetrievalResult]
    ) -> List[RetrievalResult]:
        """
        加权融合（线性加权）

        Args:
            vector_results: 向量检索结果
            bm25_results: BM25检索结果
            alpha: 向量检索权重

        Returns:
            List[RetrievalResult]: 融合后的结果列表
        """
        # 归一化分数
        vector_results = self.normalize_scores(vector_results)
        bm25_results = self.normalize_scores(bm25_results)

        # 创建结果映射
        result_map: Dict[str, RetrievalResult] = {}

        # 处理向量检索结果
        for result in vector_results:
            result_map[result.chunk_id] = {
                "result": result,
                "combined_score": result.score * self.alpha
            }

        # 处理BM25结果，累加分数
        for result in bm25_results:
            chunk_id = result.chunk_id
            if chunk_id in result_map:
                result_map[chunk_id]["combined_score"] += result.score * (1 - self.alpha)
            else:
                result_map[chunk_id] = {
                    "result": result,
                    "combined_score": result.score * (1 - self.alpha)
                }

        # 排序
        sorted_items = sorted(
            result_map.values(),
            key=lambda x: x["combined_score"],
            reverse=True
        )

        # 更新分数
        for item in sorted_items:
            item["result"].score = item["combined_score"]

        return [item["result"] for item in sorted_items]
