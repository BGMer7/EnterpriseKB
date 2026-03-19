"""
Milvus向量数据库客户端
支持Collection管理、向量索引、数据CRUD操作
"""
import asyncio
from typing import List, Optional, Dict, Any, Tuple
from contextlib import asynccontextmanager

from pymilvus import (
    Collection, FieldSchema, CollectionSchema, DataType,
    connections
)
from pymilvus import MilvusClient

from app.config import settings
from app.core.constants import Permissions
from app.core.permissions import get_user_role_names


class MilvusClientWrapper:
    """
    Milvus客户端包装类
    支持本地 Milvus 和 Zilliz Cloud 云端连接
    """

    def __init__(
        self,
        host: str = settings.MILVUS_HOST,
        port: int = settings.MILVUS_PORT,
        collection_name: str = settings.MILVUS_COLLECTION_NAME,
        dimension: int = settings.MILVUS_DIMENSION,
        cloud_uri: str = settings.MILVUS_CLOUD_URI,
        cloud_user: str = settings.MILVUS_CLOUD_USER,
        cloud_password: str = settings.MILVUS_CLOUD_PASSWORD
    ):
        self.host = host
        self.port = port
        self.collection_name = collection_name
        self.dimension = dimension
        self.cloud_uri = cloud_uri
        self.cloud_user = cloud_user
        self.cloud_password = cloud_password
        self._client = None
        self._collection = None
        self._is_cloud = bool(cloud_uri and cloud_user and cloud_password)

    def connect(self) -> MilvusClient:
        """
        连接到Milvus服务器
        支持本地连接和 Zilliz Cloud 云端连接
        """
        if self._client is None:
            if self._is_cloud:
                # Zilliz Cloud 云端连接 (使用 Token)
                self._client = MilvusClient(
                    uri=self.cloud_uri,
                    token=self.cloud_password  # 直接使用 Token
                )
            else:
                # 本地 Milvus 连接
                self._client = MilvusClient(
                    host=self.host,
                    port=self.port,
                    alias="default"
                )
        return self._client

    def disconnect(self):
        """
        断开连接
        """
        if self._client:
            connections.disconnect(alias="default")
            self._client = None
            self._collection = None

    @property
    def client(self) -> MilvusClient:
        """获取Milvus客户端"""
        if self._client is None:
            self.connect()
        return self._client

    def check_health(self) -> str:
        """
        检查Milvus健康状态
        """
        try:
            self.client.list_collections()
            return "healthy"
        except Exception as e:
            return f"unhealthy: {str(e)}"

    # ===== Collection管理 =====
    def create_collection(self, overwrite: bool = False) -> bool:
        """
        创建Collection

        Args:
            overwrite: 是否覆盖已存在的Collection

        Returns:
            bool: 是否创建成功
        """
        client = self.client

        # 检查Collection是否存在
        if client.has_collection(self.collection_name):
            if overwrite:
                client.drop_collection(self.collection_name)
            else:
                print(f"Collection {self.collection_name} already exists")
                return False

        # 定义Schema
        fields = [
            # 主键字段（自动生成）
            FieldSchema(
                name="id",
                dtype=DataType.VARCHAR,
                max_length=64,
                is_primary=True,
                auto_id=True,
                description="Primary key"
            ),
            # 关联字段
            FieldSchema(
                name="chunk_id",
                dtype=DataType.VARCHAR,
                max_length=64,
                description="关联SQLite chunk ID"
            ),
            FieldSchema(
                name="document_id",
                dtype=DataType.VARCHAR,
                max_length=64,
                description="关联SQLite document ID"
            ),
            # 内容字段
            FieldSchema(
                name="content",
                dtype=DataType.VARCHAR,
                max_length=65535,
                description="Chunk content"
            ),
            FieldSchema(
                name="title",
                dtype=DataType.VARCHAR,
                max_length=500,
                description="Document title"
            ),
            # 权限字段
            FieldSchema(
                name="department_id",
                dtype=DataType.VARCHAR,
                max_length=64,
                description="Department ID for permission filtering"
            ),
            FieldSchema(
                name="is_public",
                dtype=DataType.BOOL,
                description="Whether document is public"
            ),
            FieldSchema(
                name="allowed_roles",
                dtype=DataType.ARRAY,
                max_capacity=10,
                element_type=DataType.VARCHAR,
                max_length=50,
                description="Allowed roles for permission filtering"
            ),
            # 元数据字段
            FieldSchema(
                name="page_number",
                dtype=DataType.INT64,
                description="Page number"
            ),
            FieldSchema(
                name="section",
                dtype=DataType.VARCHAR,
                max_length=100,
                description="Section title"
            ),
            FieldSchema(
                name="chunk_index",
                dtype=DataType.INT64,
                description="Chunk index in document"
            ),
            FieldSchema(
                name="created_at",
                dtype=DataType.INT64,
                description="Creation timestamp"
            ),
            # 向量字段
            FieldSchema(
                name="embedding",
                dtype=DataType.FLOAT_VECTOR,
                dim=self.dimension,
                description="BGE-M3 embedding"
            ),
        ]

        schema = CollectionSchema(
            fields=fields,
            description="Enterprise documents collection",
            enable_dynamic_field=True
        )

        # 创建Collection
        client.create_collection(
            collection_name=self.collection_name,
            schema=schema
        )

        # 创建向量索引
        index_params = {
            "index_type": "HNSW",
            "metric_type": "COSINE",
            "params": {
                "M": 16,
                "efConstruction": 100
            }
        }
        client.create_index(
            collection_name=self.collection_name,
            field_name="embedding",
            index_params=index_params
        )

        # 创建标量字段索引（用于权限过滤）
        scalar_fields = ["department_id", "is_public", "created_at"]
        for field in scalar_fields:
            index_type = "BITMAP" if field == "is_public" else "INVERTED"
            try:
                client.create_index(
                    collection_name=self.collection_name,
                    field_name=field,
                    index_type=index_type
                )
            except Exception as e:
                print(f"Warning: Failed to create index for {field}: {e}")

        print(f"Collection {self.collection_name} created successfully")
        return True

    def drop_collection(self) -> bool:
        """
        删除Collection

        Returns:
            bool: 是否删除成功
        """
        client = self.client
        if client.has_collection(self.collection_name):
            client.drop_collection(self.collection_name)
            print(f"Collection {self.collection_name} dropped")
            return True
        return False

    def get_collection(self) -> Collection:
        """
        获取Collection对象

        Returns:
            Collection: Milvus Collection对象
        """
        if self._collection is None:
            from pymilvus import Collection
            self._collection = Collection(self.collection_name)
        return self._collection

    def load_collection(self):
        """
        加载Collection到内存
        """
        collection = self.get_collection()
        if not collection.is_empty and collection.load_state != "Loaded":
            collection.load()
            print(f"Collection {self.collection_name} loaded to memory")

    def release_collection(self):
        """
        释放Collection内存
        """
        collection = self.get_collection()
        if collection.load_state == "Loaded":
            collection.release()
            print(f"Collection {self.collection_name} released from memory")

    # ===== 数据操作 =====
    def insert_chunks(
        self,
        chunks: List[Dict[str, Any]]
    ) -> List[str]:
        """
        插入文档块数据

        Args:
            chunks: 文档块数据列表
                {
                    "chunk_id": str,
                    "document_id": str,
                    "content": str,
                    "title": str,
                    "department_id": Optional[str],
                    "is_public": bool,
                    "allowed_roles": List[str],
                    "page_number": Optional[int],
                    "section": Optional[str],
                    "chunk_index": int,
                    "embedding": List[float],
                }

        Returns:
            List[str]: Milvus ID列表
        """
        client = self.client

        if not chunks:
            return []

        # 准备数据
        data = []
        for chunk in chunks:
            data.append({
                "chunk_id": chunk["chunk_id"],
                "document_id": chunk["document_id"],
                "content": chunk["content"],
                "title": chunk["title"],
                "department_id": chunk.get("department_id"),
                "is_public": chunk.get("is_public", False),
                "allowed_roles": chunk.get("allowed_roles", []),
                "page_number": chunk.get("page_number"),
                "section": chunk.get("section"),
                "chunk_index": chunk["chunk_index"],
                "embedding": chunk["embedding"],
            })

        # 插入数据
        insert_result = client.insert(
            collection_name=self.collection_name,
            data=data
        )

        # 刷新（使数据可搜索）
        client.flush(self.collection_name)

        return insert_result["ids"]

    def delete_chunks(self, chunk_ids: List[str]) -> int:
        """
        删除文档块数据

        Args:
            chunk_ids: SQLite chunk ID列表

        Returns:
            int: 删除的数量
        """
        client = self.client

        # 先查询Milvus ID
        results = client.query(
            collection_name=self.collection_name,
            filter=f"chunk_id in {json.dumps(chunk_ids)}",
            output_fields=["id"]
        )

        milvus_ids = [r["id"] for r in results] if results else []

        if not milvus_ids:
            return 0

        # 删除数据
        client.delete(
            collection_name=self.collection_name,
            ids=milvus_ids
        )

        return len(milvus_ids)

    def delete_by_document(self, document_id: str) -> int:
        """
        根据文档ID删除所有相关chunk

        Args:
            document_id: SQLite document ID

        Returns:
            int: 删除的数量
        """
        client = self.client

        # 查询Milvus ID
        results = client.query(
            collection_name=self.collection_name,
            filter=f'document_id == "{document_id}"',
            output_fields=["id"]
        )

        milvus_ids = [r["id"] for r in results] if results else []

        if not milvus_ids:
            return 0

        # 删除数据
        client.delete(
            collection_name=self.collection_name,
            ids=milvus_ids
        )

        return len(milvus_ids)

    # ===== 检索操作 =====
    def search(
        self,
        query_embedding: List[float],
        top_k: int = 30,
        filter_expression: Optional[str] = None,
        output_fields: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        向量检索

        Args:
            query_embedding: 查询向量
            top_k: 返回结果数量
            filter_expression: 过滤表达式（用于权限控制）
            output_fields: 返回字段列表

        Returns:
            List[Dict]: 检索结果列表
        """
        client = self.client

        # 确保Collection已加载
        if not client.get_load_state(self.collection_name) == "Loaded":
            client.load_collection(self.collection_name)

        # 设置输出字段
        if output_fields is None:
            output_fields = [
                "chunk_id", "document_id", "content", "title",
                "department_id", "is_public", "allowed_roles",
                "page_number", "section", "chunk_index"
            ]

        # 执行检索
        results = client.search(
            collection_name=self.collection_name,
            data=[query_embedding],
            limit=top_k,
            filter=filter_expression,
            output_fields=output_fields
        )

        # 格式化结果
        formatted_results = []
        for result in results[0]:
            formatted_results.append({
                "id": result["id"],
                "score": result["distance"],  # Milvus返回的是距离，越小越好
                "chunk_id": result["entity"].get("chunk_id"),
                "document_id": result["entity"].get("document_id"),
                "content": result["entity"].get("content"),
                "title": result["entity"].get("title"),
                "department_id": result["entity"].get("department_id"),
                "is_public": result["entity"].get("is_public"),
                "allowed_roles": result["entity"].get("allowed_roles", []),
                "page_number": result["entity"].get("page_number"),
                "section": result["entity"].get("section"),
                "chunk_index": result["entity"].get("chunk_index"),
            })

        return formatted_results

    def build_permission_filter(
        self,
        department_id: Optional[str],
        roles: List[str]
    ) -> str:
        """
        构建权限过滤表达式

        Args:
            department_id: 用户部门ID
            roles: 用户角色列表

        Returns:
            str: Milvus过滤表达式
        """
        conditions = []

        # 公开文档
        conditions.append('is_public == true')

        # 同部门文档
        if department_id:
            conditions.append(f'department_id == "{department_id}"')

        # 角色允许的文档
        for role in roles:
            conditions.append(f'"{role}" in allowed_roles')

        # 使用OR连接
        return " or ".join(conditions)

    # ===== 统计信息 =====
    def get_collection_stats(self) -> Dict[str, Any]:
        """
        获取Collection统计信息

        Returns:
            Dict: 统计信息
        """
        client = self.client

        if not client.has_collection(self.collection_name):
            return {
                "exists": False,
                "count": 0
            }

        collection = self.get_collection()
        collection.load()

        return {
            "exists": True,
            "name": self.collection_name,
            "count": collection.num_entities,
            "schema": collection.schema,
            "index": collection.indexes,
        }


# 全局Milvus客户端实例
milvus_client = MilvusClientWrapper()


def get_milvus_client() -> MilvusClientWrapper:
    """获取Milvus客户端单例"""
    return milvus_client
