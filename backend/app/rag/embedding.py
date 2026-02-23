"""
Embedding模型管理
支持BGE-M3等中文embedding模型
"""
from typing import List, Union
import torch
from sentence_transformers import SentenceTransformer
from FlagEmbedding import BGEM3FlagModel

from app.config import settings


class EmbeddingModel:
    """
    Embedding模型基类
    """

    def __init__(self, model_name: str, device: str = None):
        self.model_name = model_name
        self.device = device or settings.EMBEDDING_DEVICE
        self._model = None
        self._dimension = None

    def encode(
        self,
        texts: Union[str, List[str]],
        batch_size: int = 32
    ) -> torch.Tensor:
        """
        编码文本为向量

        Args:
            texts: 文本或文本列表
            batch_size: 批处理大小

        Returns:
            torch.Tensor: 向量或向量矩阵
        """
        raise NotImplementedError

    @property
    def dimension(self) -> int:
        """获取向量维度"""
        if self._dimension is None:
            # 单次编码获取维度
            result = self.encode(["test"])
            self._dimension = result.shape[-1]
        return self._dimension

    def to(self, device: str):
        """移动模型到指定设备"""
        self.device = device
        if self._model:
            self._model.to(device)
        return self


class BGEModel(EmbeddingModel):
    """
    BGE系列Embedding模型
    支持BGE-M3等多语言模型
    """

    def __init__(
        self,
        model_name: str = settings.EMBEDDING_MODEL,
        device: str = None,
        use_fp16: bool = True
    ):
        super().__init__(model_name, device)
        self.use_fp16 = use_fp16
        self._load_model()

    def _load_model(self):
        """加载模型"""
        if "bge-m3" in self.model_name.lower():
            # 使用BGE-M3
            self._model = BGEM3FlagModel(
                self.model_name,
                use_fp16=self.use_fp16
            )
        else:
            # 使用通用SentenceTransformer
            self._model = SentenceTransformer(
                self.model_name,
                device=self.device
            )

    def encode(
        self,
        texts: Union[str, List[str]],
        batch_size: int = 32
    ) -> torch.Tensor:
        """
        编码文本为向量

        Args:
            texts: 文本或文本列表
            batch_size: 批处理大小

        Returns:
            torch.Tensor: 向量或向量矩阵
        """
        if isinstance(texts, str):
            texts = [texts]

        # BGE-M3特殊处理
        if "bge-m3" in self.model_name.lower():
            embeddings = self._model.encode(
                texts,
                batch_size=batch_size,
                return_dense=True
            )["dense_vecs"]
            return torch.tensor(embeddings)
        else:
            embeddings = self._model.encode(
                texts,
                batch_size=batch_size,
                show_progress_bar=False
            )
            return torch.tensor(embeddings)

    def encode_queries(
        self,
        queries: Union[str, List[str]],
        batch_size: int = 32
    ) -> torch.Tensor:
        """
        编码查询（查询和文档使用不同的encode方法可以提升效果）
        """
        if isinstance(queries, str):
            queries = [queries]

        # BGE-M3支持查询模式
        if "bge-m3" in self.model_name.lower():
            embeddings = self._model.encode(
                queries,
                batch_size=batch_size,
                return_dense=True
            )["dense_vecs"]
            return torch.tensor(embeddings)
        else:
            # 通用模型直接encode
            return self.encode(queries, batch_size)

    @property
    def dimension(self) -> int:
        """获取向量维度"""
        if self._dimension is None:
            if "bge-m3" in self.model_name.lower():
                self._dimension = 1024
            else:
                # 通用模型获取维度
                result = self.encode(["test"])
                self._dimension = result.shape[-1]
        return self._dimension


# 全局Embedding模型实例
_embedding_model: EmbeddingModel = None


def get_embedding_model() -> EmbeddingModel:
    """
    获取Embedding模型单例

    Returns:
        EmbeddingModel: Embedding模型实例
    """
    global _embedding_model

    if _embedding_model is None:
        _embedding_model = BGEModel(
            model_name=settings.EMBEDDING_MODEL,
            device=settings.EMBEDDING_DEVICE
        )

    return _embedding_model


def encode_text(text: Union[str, List[str]]) -> List[List[float]]:
    """
    编码文本为向量（便捷函数）

    Args:
        text: 文本或文本列表

    Returns:
        List[List[float]]: 向量列表
    """
    model = get_embedding_model()
    embeddings = model.encode(text)
    return embeddings.tolist()


def encode_query(query: str) -> List[float]:
    """
    编码查询为向量（便捷函数）

    Args:
        query: 查询文本

    Returns:
        List[float]: 向量
    """
    model = get_embedding_model()
    embedding = model.encode_queries(query)
    return embedding.squeeze().tolist()
