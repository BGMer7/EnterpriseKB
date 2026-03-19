"""
EnterpriseKB 配置管理
使用 pydantic-settings 进行配置管理
"""
from functools import lru_cache
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # ===== 项目信息 =====
    PROJECT_NAME: str = "EnterpriseKB"
    VERSION: str = "1.0.0"
    DEBUG: bool = False

    # ===== API配置 =====
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    WORKERS: int = 4
    SHOW_DOCS: bool = True

    # ===== CORS配置 =====
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
    ]

    # ===== 数据库配置 =====
    DATABASE_URL: str = "sqlite+aiosqlite:///./enterprisekb.db"
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 10
    DATABASE_POOL_TIMEOUT: int = 30
    DATABASE_POOL_RECYCLE: int = 3600

    # ===== Redis配置 =====
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_CACHE_TTL: int = 3600  # 1小时

    # ===== Milvus配置 =====
    # 本地 Milvus
    MILVUS_HOST: str = "localhost"
    MILVUS_PORT: int = 19530
    # Zilliz Cloud (云端 Milvus)
    MILVUS_CLOUD_URI: str = ""  # 如: https://xxxxx.api.zillizcloud.com
    MILVUS_CLOUD_USER: str = ""  # 集群 ID
    MILVUS_CLOUD_PASSWORD: str = ""  # Zilliz Cloud 密码
    # 通用配置
    MILVUS_COLLECTION_NAME: str = "enterprise_documents"
    MILVUS_DIMENSION: int = 1024  # BGE-M3 embedding维度

    # ===== Meilisearch配置 =====
    MEILISEARCH_URL: str = "http://localhost:7700"
    MEILISEARCH_INDEX_NAME: str = "documents_bm25"
    MEILISEARCH_API_KEY: str = ""

    # ===== LLM配置 (vLLM) =====
    LLM_API_URL: str = "http://localhost:8000/v1"
    LLM_MODEL_NAME: str = "Qwen/Qwen2.5-14B-Instruct"
    LLM_MAX_TOKENS: int = 2000
    LLM_TEMPERATURE: float = 0.1
    LLM_TIMEOUT: int = 60  # 秒

    # ===== Embedding配置 =====
    EMBEDDING_MODEL: str = "BAAI/bge-m3"
    EMBEDDING_DEVICE: str = "cuda"
    EMBEDDING_BATCH_SIZE: int = 32

    # ===== Reranker配置 =====
    RERANKER_MODEL: str = "BAAI/bge-reranker-base"
    RERANKER_TOP_K: int = 15
    RERANKER_BATCH_SIZE: int = 16

    # ===== JWT配置 =====
    JWT_SECRET_KEY: str = "your-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 120  # 2小时
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ===== 企业微信配置 =====
    WECHAT_CORP_ID: str = ""
    WECHAT_APP_SECRET: str = ""
    WECHAT_APP_ID: str = ""
    WECHAT_TOKEN: str = ""
    WECHAT_ENCODING_AES_KEY: str = ""

    # ===== MinIO配置 =====
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_SECURE: bool = False
    MINIO_BUCKET_NAME: str = "enterprisekb-docs"

    # ===== RabbitMQ配置 =====
    RABBITMQ_URL: str = "amqp://guest:guest@localhost:5672/"

    # ===== 文档处理配置 =====
    MAX_FILE_SIZE: int = 50 * 1024 * 1024  # 50MB
    ALLOWED_FILE_TYPES: List[str] = [
        "pdf", "docx", "xlsx", "txt", "md"
    ]
    CHUNK_SIZE: int = 512  # tokens
    CHUNK_OVERLAP: int = 50  # tokens

    # ===== 日志配置 =====
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # ===== 权限配置 =====
    DEFAULT_ROLE: str = "REGULAR_USER"
    ADMIN_ROLE: str = "SUPER_ADMIN"

    # ===== RAG配置 =====
    RAG_TOP_K: int = 30  # 检索前K个结果
    RAG_FUSION_K: int = 60  # RRF融合参数
    RAG_MIN_SCORE: float = 0.7  # 最低相关性分数
    RAG_MAX_CONTEXT_TOKENS: int = 4000  # 最大上下文token数


@lru_cache
def get_settings() -> Settings:
    """获取配置单例"""
    return Settings()


settings = get_settings()
