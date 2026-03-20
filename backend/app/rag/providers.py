"""
RAG Provider 配置
定义支持的RAG检索provider类型
"""
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class RAGProviderType(str, Enum):
    """
    RAG Provider 类型

    - custom: 现有 HybridRetriever (Milvus + Meilisearch)
    - langchain: LangChain 实现
    - llamaindex: LlamaIndex 实现
    - milvus: Milvus 原生混合检索 (dense + sparse)
    """
    CUSTOM = "custom"
    LANGCHAIN = "langchain"
    LLAMAINDEX = "llamaindex"
    MILVUS = "milvus"


class RAGProviderConfig(BaseModel):
    """
    RAG Provider 配置

    用于在创建 retriever 时传递配置
    """
    provider: RAGProviderType = RAGProviderType.CUSTOM
    # 通用配置
    top_k: int = 30
    # LangChain 特定配置
    langchain_embedding_model: Optional[str] = None
    # LlamaIndex 特定配置
    llamaindex_embedding_model: Optional[str] = None
    # Milvus 原生混合检索特定配置
    milvus_sparse_weight: float = 0.3  # sparse vector 在融合时的权重
    milvus_dense_top_k: int = 30
    milvus_sparse_top_k: int = 30
    milvus_fusion_k: int = 60


# 全局默认配置
default_provider_config = RAGProviderConfig()