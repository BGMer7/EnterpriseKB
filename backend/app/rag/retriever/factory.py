"""
RAG Retriever 工厂函数
根据 provider 类型创建对应的 retriever 实例
"""
from typing import Optional, List, Dict, Any
import logging

from app.config import settings
from app.rag.providers import RAGProviderType, RAGProviderConfig
from app.rag.retriever.base import BaseRetriever

logger = logging.getLogger(__name__)


# Lazy imports for provider-specific retrievers
_langchain_retriever = None
_llamaindex_retriever = None
_milvus_hybrid_retriever = None


def _get_langchain_retriever_class():
    """Lazy load LangChainRetriever"""
    global _langchain_retriever
    if _langchain_retriever is None:
        try:
            from app.rag.retriever.langchain_retriever import LangChainRetriever
            _langchain_retriever = LangChainRetriever
        except ImportError as e:
            logger.warning(f"LangChainRetriever not available: {e}")
            raise ImportError(
                "LangChain is not installed. Install with: pip install langchain langchain-milvus langchain-openai"
            ) from e
    return _langchain_retriever


def _get_llamaindex_retriever_class():
    """Lazy load LlamaIndexRetriever"""
    global _llamaindex_retriever
    if _llamaindex_retriever is None:
        try:
            from app.rag.retriever.llamaindex_retriever import LlamaIndexRetriever
            _llamaindex_retriever = LlamaIndexRetriever
        except ImportError as e:
            logger.warning(f"LlamaIndexRetriever not available: {e}")
            raise ImportError(
                "LlamaIndex is not installed. Install with: pip install llama-index llama-index-vector-stores-milvus"
            ) from e
    return _llamaindex_retriever


def _get_milvus_hybrid_retriever_class():
    """Lazy load MilvusHybridRetriever"""
    global _milvus_hybrid_retriever
    if _milvus_hybrid_retriever is None:
        try:
            from app.rag.retriever.milvus_hybrid_retriever import MilvusHybridRetriever
            _milvus_hybrid_retriever = MilvusHybridRetriever
        except ImportError as e:
            logger.warning(f"MilvusHybridRetriever not available: {e}")
            raise ImportError(
                "MilvusHybridRetriever not available. Make sure pymilvus is installed."
            ) from e
    return _milvus_hybrid_retriever


def create_retriever(
    provider: Optional[str] = None,
    config: Optional[RAGProviderConfig] = None,
    **kwargs
) -> BaseRetriever:
    """
    工厂函数，根据 provider 类型创建对应的 retriever

    Args:
        provider: Provider 名称 ("custom", "langchain", "llamaindex", "milvus")
        config: RAGProviderConfig 配置对象
        **kwargs: 其他传递给 retriever 的参数

    Returns:
        BaseRetriever: retriever 实例

    Raises:
        ValueError: 不支持的 provider
        ImportError: provider 未安装
    """
    # 确定 provider
    if provider is None:
        if config is not None:
            provider = config.provider.value
        else:
            provider = settings.RAG_PROVIDER if hasattr(settings, 'RAG_PROVIDER') else "custom"

    # 获取配置
    if config is None:
        config = RAGProviderConfig()

    # 创建对应的 retriever
    if provider == RAGProviderType.CUSTOM.value or provider == "custom":
        return _create_custom_retriever(config, **kwargs)
    elif provider == RAGProviderType.LANGCHAIN.value or provider == "langchain":
        return _create_langchain_retriever(config, **kwargs)
    elif provider == RAGProviderType.LLAMAINDEX.value or provider == "llamaindex":
        return _create_llamaindex_retriever(config, **kwargs)
    elif provider == RAGProviderType.MILVUS.value or provider == "milvus":
        return _create_milvus_hybrid_retriever(config, **kwargs)
    else:
        raise ValueError(
            f"Unknown RAG provider: {provider}. "
            f"Available providers: {[p.value for p in RAGProviderType]}"
        )


def _create_custom_retriever(config: RAGProviderConfig, **kwargs) -> BaseRetriever:
    """创建现有的 HybridRetriever (Milvus + Meilisearch)"""
    from app.rag.retriever.hybrid_retriever import HybridRetriever

    return HybridRetriever(
        vector_top_k=kwargs.get("vector_top_k", config.top_k * 2),
        bm25_top_k=kwargs.get("bm25_top_k", config.top_k * 2),
        fusion_k=kwargs.get("fusion_k", 60),
        alpha=kwargs.get("alpha", 0.5)
    )


def _create_langchain_retriever(config: RAGProviderConfig, **kwargs) -> BaseRetriever:
    """创建 LangChain-based retriever"""
    cls = _get_langchain_retriever_class()

    return cls(
        collection_name=kwargs.get("collection_name", settings.MILVUS_COLLECTION_NAME),
        embedding_model=config.langchain_embedding_model or settings.EMBEDDING_MODEL,
        top_k=kwargs.get("top_k", config.top_k)
    )


def _create_llamaindex_retriever(config: RAGProviderConfig, **kwargs) -> BaseRetriever:
    """创建 LlamaIndex-based retriever"""
    cls = _get_llamaindex_retriever_class()

    return cls(
        collection_name=kwargs.get("collection_name", settings.MILVUS_COLLECTION_NAME),
        embedding_model=config.llamaindex_embedding_model or settings.EMBEDDING_MODEL,
        top_k=kwargs.get("top_k", config.top_k)
    )


def _create_milvus_hybrid_retriever(config: RAGProviderConfig, **kwargs) -> BaseRetriever:
    """创建 Milvus 原生混合检索 retriever"""
    cls = _get_milvus_hybrid_retriever_class()

    return cls(
        collection_name=kwargs.get("collection_name", settings.MILVUS_COLLECTION_NAME),
        dense_top_k=kwargs.get("dense_top_k", config.milvus_dense_top_k),
        sparse_top_k=kwargs.get("sparse_top_k", config.milvus_sparse_top_k),
        fusion_k=kwargs.get("fusion_k", config.milvus_fusion_k),
        sparse_weight=kwargs.get("sparse_weight", config.milvus_sparse_weight)
    )


def get_available_providers() -> List[Dict[str, Any]]:
    """
    获取所有可用的 provider 信息

    Returns:
        List[Dict]: provider 信息列表
    """
    providers = []

    # Custom - always available
    providers.append({
        "name": "custom",
        "display_name": "Custom (Milvus + Meilisearch)",
        "description": "现有实现：Milvus 向量检索 + Meilisearch BM25 混合检索",
        "available": True
    })

    # LangChain
    try:
        _get_langchain_retriever_class()
        langchain_available = True
    except ImportError:
        langchain_available = False
    providers.append({
        "name": "langchain",
        "display_name": "LangChain",
        "description": "使用 LangChain 框架的 Milvus 集成",
        "available": langchain_available
    })

    # LlamaIndex
    try:
        _get_llamaindex_retriever_class()
        llamaindex_available = True
    except ImportError:
        llamaindex_available = False
    providers.append({
        "name": "llamaindex",
        "display_name": "LlamaIndex",
        "description": "使用 LlamaIndex 框架的 Milvus 向量存储",
        "available": llamaindex_available
    })

    # Milvus Native
    try:
        _get_milvus_hybrid_retriever_class()
        milvus_available = True
    except ImportError:
        milvus_available = False
    providers.append({
        "name": "milvus",
        "display_name": "Milvus Native Hybrid",
        "description": "Milvus 2.4+ 原生 dense + sparse 混合检索",
        "available": milvus_available
    })

    return providers
