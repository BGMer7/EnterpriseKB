"""
BGE Reranker重排序器
使用BGE系列cross-encoder模型对检索结果进行重排序
"""
from typing import List, Dict, Any, Optional
from functools import lru_cache

import torch
from FlagEmbedding import BGEM3FlagModel

from app.config import settings


class BGEReranker:
    """
    BGE Reranker
    使用cross-encoder对检索结果重新排序
    """

    def __init__(
        self,
        model_name: str = settings.RERANKER_MODEL,
        device: str = None,
        top_k: int = settings.RERANKER_TOP_K,
        batch_size: int = 16
    ):
        self.model_name = model_name
        self.device = device or settings.EMBEDDING_DEVICE
        self.top_k = top_k
        self.batch_size = batch_size
        self._model = None

    def load_model(self):
        """加载reranker模型"""
        if self._model is None:
            self._model = BGEM3FlagModel(
                self.model_name,
                use_fp16=True,
                device=self.device
            )

    def rerank(
        self,
        query: str,
        documents: List[Dict[str, Any]],
        top_k: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        重排序检索结果

        Args:
            query: 查询文本
            documents: 检索结果列表
                [
                    {
                        "id": str,
                        "content": str,
                        "score": float,
                        ...
                    },
                    ...
                ]
            top_k: 返回前K个结果

        Returns:
            List[Dict]: 重排序后的结果列表
        """
        if not documents:
            return []

        if len(documents) <= 1:
            return documents

        self.load_model()

        k = top_k or self.top_k

        # 提取文档内容
        doc_contents = [doc["content"] for doc in documents]

        # 计算相关性分数
        scores = self._model.compute_score(
            [[query, doc] for doc in doc_contents],
            batch_size=self.batch_size,
            max_length=512
        )

        # 处理分数
        if isinstance(scores, torch.Tensor):
            scores = scores.tolist()

        # 添加rerank分数到结果
        for doc, score in zip(documents, scores):
            doc["rerank_score"] = score

        # 按rerank分数排序（分数越高越好）
        reranked = sorted(
            documents,
            key=lambda x: x.get("rerank_score", 0),
            reverse=True
        )

        # 返回top_k
        return reranked[:k]

    def rerank_pairwise(
        self,
        query: str,
        documents: List[Dict[str, Any]],
        top_k: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        使用成对比较的方式重排序（更准确但更慢）

        Args:
            query: 查询文本
            documents: 检索结果列表
            top_k: 返回前K个结果

        Returns:
            List[Dict]: 重排序后的结果列表
        """
        if not documents:
            return []

        if len(documents) <= 1:
            return documents

        self.load_model()

        k = top_k or self.top_k

        # 提取文档内容
        doc_contents = [doc["content"] for doc in documents]

        # 成对比较
        scores = self._model.compute_score(
            [[query, doc] for doc in doc_contents],
            batch_size=self.batch_size,
            max_length=512,
            normalize=True
        )

        # 处理分数
        if isinstance(scores, torch.Tensor):
            scores = scores.tolist()

        # 添加rerank分数到结果
        for doc, score in zip(documents, scores):
            doc["rerank_score"] = score

        # 按rerank分数排序
        reranked = sorted(
            documents,
            key=lambda x: x.get("rerank_score", 0),
            reverse=True
        )

        return reranked[:k]


# 全局Reranker实例
_reranker: Optional[BGEReranker] = None


def get_reranker() -> BGEReranker:
    """
    获取Reranker单例

    Returns:
        BGEReranker: Reranker实例
    """
    global _reranker

    if _reranker is None:
        _reranker = BGEReranker()

    return _reranker


def rerank_results(
    query: str,
    results: List[Dict[str, Any]],
    top_k: int = None
) -> List[Dict[str, Any]]:
    """
    重排序检索结果（便捷函数）

    Args:
        query: 查询文本
        results: 检索结果列表
        top_k: 返回前K个结果

    Returns:
        List[Dict]: 重排序后的结果列表
    """
    reranker = get_reranker()
    return reranker.rerank(query, results, top_k)
