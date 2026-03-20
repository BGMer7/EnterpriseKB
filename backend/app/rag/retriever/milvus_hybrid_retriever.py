"""
Milvus Native Hybrid Retriever
使用 Milvus 2.4+ 的 dense + sparse 向量混合检索

注意：此实现需要 Milvus 2.4+ 并且 collection 已配置 sparse_vector 字段
"""
from typing import List, Optional, Dict, Any, Tuple
import logging
import asyncio
from collections import defaultdict

from app.rag.retriever.base import BaseRetriever, RetrievalResult
from app.rag.embedding import encode_query
from app.config import settings

logger = logging.getLogger(__name__)


class MilvusHybridRetriever(BaseRetriever):
    """
    Milvus 原生混合检索器

    使用 Milvus 2.4+ 的 dense 向量 + sparse 向量 (BM25风格) 混合检索。
    所有检索在 Milvus 内部完成，无需外部 BM25 服务。

    要求：
    - Milvus 2.4+
    - Collection 已添加 sparse_vector 字段
    """

    def __init__(
        self,
        collection_name: str = settings.MILVUS_COLLECTION_NAME,
        dense_top_k: int = 30,
        sparse_top_k: int = 30,
        fusion_k: int = 60,
        sparse_weight: float = 0.3
    ):
        self.collection_name = collection_name
        self.dense_top_k = dense_top_k
        self.sparse_top_k = sparse_top_k
        self.fusion_k = fusion_k
        self.sparse_weight = sparse_weight  # sparse vector 在融合时的权重
        self._milvus_client = None

    @property
    def milvus_client(self):
        """Lazy-load Milvus client"""
        if self._milvus_client is None:
            from app.integrations.milvus_client import get_milvus_client
            self._milvus_client = get_milvus_client().client
        return self._milvus_client

    async def retrieve(
        self,
        query: str,
        top_k: int = 30,
        filter_expression: Optional[str] = None
    ) -> List[RetrievalResult]:
        """
        Milvus 原生混合检索

        同时执行 dense 向量检索和 sparse 向量检索，使用 RRF 融合。

        Args:
            query: 查询文本
            top_k: 返回结果数量
            filter_expression: 过滤表达式

        Returns:
            List[RetrievalResult]: 融合后的检索结果列表
        """
        # 1. 获取 dense embedding
        dense_embedding = await self._get_dense_embedding(query)

        # 2. 获取 sparse vector (BM25风格)
        sparse_vector = await self._compute_sparse_vector(query)

        # 3. 并行执行 dense 和 sparse 检索
        dense_results, sparse_results = await asyncio.gather(
            self._search_dense(dense_embedding, top_k, filter_expression),
            self._search_sparse(sparse_vector, top_k, filter_expression)
        )

        # 4. RRF 融合
        fused_results = self._reciprocal_rank_fusion(
            [dense_results, sparse_results],
            k=self.fusion_k
        )

        return fused_results[:top_k]

    async def _get_dense_embedding(self, query: str) -> List[float]:
        """获取 query 的 dense embedding"""
        # 使用现有的 embedding 函数
        embeddings = await asyncio.to_thread(encode_query, query)
        return embeddings[0].tolist() if hasattr(embeddings[0], 'tolist') else list(embeddings[0])

    async def _compute_sparse_vector(self, query: str) -> Dict[str, Any]:
        """
        计算 query 的 sparse vector (BM25风格)

        Returns:
            Dict with "indices" and "values" keys for Milvus sparse vector format

        Note: 这是简化实现。在生产环境中，应该：
        1. 使用与建索引时相同的分词器
        2. 使用相同的 IDF 权重
        3. 考虑使用 Milvus 提供的 BM25 函数
        """
        # 简单的词频统计作为 sparse vector
        # 实际实现应该使用 jieba 分词 + BM25 IDF 权重
        words = query.lower().split()

        # 统计词频
        word_freq = defaultdict(int)
        for word in words:
            if len(word) > 1:  # 忽略单字符
                word_freq[word] += 1

        if not word_freq:
            return {"indices": [], "values": []}

        # 转换为 sparse vector 格式
        # 注意：实际部署时 indices 应该是词汇表中的索引
        # 这里简化为使用词汇的 hash 作为 indices
        indices = [hash(w) % 100000 for w in word_freq.keys()]
        values = list(word_freq.values())

        # 归一化 values
        max_val = max(values)
        if max_val > 0:
            values = [v / max_val for v in values]

        return {"indices": indices, "values": values}

    async def _search_dense(
        self,
        query_embedding: List[float],
        top_k: int,
        filter_expression: Optional[str]
    ) -> List[Tuple[str, float]]:
        """
        执行 dense 向量检索

        Returns:
            List of (chunk_id, score) tuples
        """
        # 确保 collection 已加载
        await asyncio.to_thread(self._ensure_loaded)

        results = await asyncio.to_thread(
            self.milvus_client.search,
            collection_name=self.collection_name,
            data=[query_embedding],
            limit=top_k or self.dense_top_k,
            filter=filter_expression,
            search_params={
                "metric_type": "COSINE",
                "params": {"ef": 128}
            },
            output_fields=["chunk_id"]
        )

        return [(r["entity"]["chunk_id"], 1.0 - r["distance"]) for r in results[0]]

    async def _search_sparse(
        self,
        sparse_vector: Dict[str, Any],
        top_k: int,
        filter_expression: Optional[str]
    ) -> List[Tuple[str, float]]:
        """
        执行 sparse 向量检索 (BM25风格)

        Returns:
            List of (chunk_id, score) tuples
        """
        # 确保 collection 已加载
        await asyncio.to_thread(self._ensure_loaded)

        try:
            # Milvus 2.4+ 的 sparse 搜索 API
            results = await asyncio.to_thread(
                self.milvus_client.search,
                collection_name=self.collection_name,
                data=[sparse_vector],  # sparse vector
                limit=top_k or self.sparse_top_k,
                filter=filter_expression,
                search_params={
                    "metric_type": "BM25",
                    "params": {}
                },
                output_fields=["chunk_id"]
            )

            return [(r["entity"]["chunk_id"], r.get("score", 0.0)) for r in results[0]]
        except Exception as e:
            logger.warning(f"Sparse search not available or failed: {e}")
            # 如果 sparse search 不可用，返回空结果
            return []

    def _ensure_loaded(self):
        """确保 collection 已加载到内存"""
        if hasattr(self.milvus_client, 'get_load_state'):
            state = self.milvus_client.get_load_state(self.collection_name)
            if state != "Loaded":
                self.milvus_client.load_collection(self.collection_name)

    def _reciprocal_rank_fusion(
        self,
        results_list: List[List[Tuple[str, float]]],
        k: int = 60
    ) -> List[RetrievalResult]:
        """
        倒数排名融合 (RRF)

        Args:
            results_list: 多个检索结果列表，每项为 (chunk_id, score) 元组
            k: RRF 参数

        Returns:
            List[RetrievalResult]: 融合后的结果
        """
        score_map: Dict[str, Dict[str, Any]] = {}

        for results in results_list:
            for rank, (chunk_id, score) in enumerate(results, 1):
                if chunk_id not in score_map:
                    score_map[chunk_id] = {
                        "score": 0,
                        "ranks": [],
                        "best_score": 0
                    }

                # RRF 分数
                rrf_score = 1 / (k + rank)
                score_map[chunk_id]["score"] += rrf_score
                score_map[chunk_id]["ranks"].append(rank)

                # 保留最佳原始分数
                if score > score_map[chunk_id]["best_score"]:
                    score_map[chunk_id]["best_score"] = score

        # 按 RRF 分数排序
        sorted_items = sorted(
            score_map.items(),
            key=lambda x: x[1]["score"],
            reverse=True
        )

        # 转换为 RetrievalResult (需要额外查询获取完整信息)
        retrieval_results = []
        for chunk_id, info in sorted_items:
            # 这里简化处理，实际应该根据 chunk_id 查询完整信息
            retrieval_results.append(RetrievalResult(
                id=chunk_id,
                chunk_id=chunk_id,
                document_id="",  # 需要查询
                content="",  # 需要查询
                title="",  # 需要查询
                score=info["score"],
                metadata={},
                department_id=None,
                is_public=None,
                allowed_roles=[],
                page_number=None,
                section=None,
                chunk_index=None,
            ))

        return retrieval_results

    async def retrieve_with_context(
        self,
        query: str,
        top_k: int = 30,
        filter_expression: Optional[str] = None
    ) -> tuple[List[RetrievalResult], str]:
        """
        检索并返回格式化的上下文

        注意：由于 Milvus hybrid 返回的结果信息不完整，
        此方法会额外查询完整文档信息。
        """
        results = await self.retrieve(query, top_k, filter_expression)

        # 补充完整信息 (通过 chunk_id 查询)
        if results:
            chunk_ids = [r.chunk_id for r in results]
            full_info = await self._get_chunk_info_batch(chunk_ids)

            for r in results:
                if r.chunk_id in full_info:
                    info = full_info[r.chunk_id]
                    r.document_id = info.get("document_id", "")
                    r.content = info.get("content", "")
                    r.title = info.get("title", "")
                    r.metadata = info.get("metadata", {})
                    r.department_id = info.get("department_id")
                    r.is_public = info.get("is_public")
                    r.allowed_roles = info.get("allowed_roles", [])
                    r.page_number = info.get("page_number")
                    r.section = info.get("section")
                    r.chunk_index = info.get("chunk_index")

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

    async def _get_chunk_info_batch(self, chunk_ids: List[str]) -> Dict[str, Dict]:
        """批量获取 chunk 的完整信息"""
        if not chunk_ids:
            return {}

        try:
            results = await asyncio.to_thread(
                self.milvus_client.query,
                collection_name=self.collection_name,
                filter=f'chunk_id in {chunk_ids}',
                output_fields=[
                    "chunk_id", "document_id", "content", "title",
                    "department_id", "is_public", "allowed_roles",
                    "page_number", "section", "chunk_index"
                ]
            )

            return {r["chunk_id"]: r for r in results}
        except Exception as e:
            logger.warning(f"Failed to query chunk info: {e}")
            return {}
