"""
Milvus Collection 初始化脚本（简化版）
用于全新的 Milvus 集群创建 Collection 和索引
"""
from pymilvus import (
    MilvusClient, FieldSchema, CollectionSchema, DataType
)

# Zilliz Cloud 配置
CLOUD_URI = "https://in03-d3a0c989c183420.serverless.ali-cn-hangzhou.cloud.zilliz.com.cn"
TOKEN = "cb3fe251c781690585cc11f3f99cdb53dd6067ce4c2e37531ddb4dccdc480794237ee5929ecf8cff7fa361b7ba7015064ff89725"
COLLECTION_NAME = "enterprise_documents"
DIMENSION = 1024


def init_milvus(overwrite: bool = False):
    """初始化 Milvus Collection"""
    # 连接
    client = MilvusClient(uri=CLOUD_URI, token=TOKEN)

    # 检查是否已存在
    if client.has_collection(COLLECTION_NAME):
        if overwrite:
            print(f"删除已存在的 Collection: {COLLECTION_NAME}")
            client.drop_collection(COLLECTION_NAME)
        else:
            print(f"Collection {COLLECTION_NAME} 已存在，跳过创建")
            return

    # 定义 Schema
    fields = [
        FieldSchema(
            name="id", dtype=DataType.VARCHAR, max_length=64,
            is_primary=True, auto_id=True, description="Primary key"
        ),
        FieldSchema(
            name="chunk_id", dtype=DataType.VARCHAR, max_length=64,
            description="关联SQLite chunk ID"
        ),
        FieldSchema(
            name="document_id", dtype=DataType.VARCHAR, max_length=64,
            description="关联SQLite document ID"
        ),
        FieldSchema(
            name="content", dtype=DataType.VARCHAR, max_length=65535,
            description="Chunk content"
        ),
        FieldSchema(
            name="title", dtype=DataType.VARCHAR, max_length=500,
            description="Document title"
        ),
        FieldSchema(
            name="department_id", dtype=DataType.VARCHAR, max_length=64,
            description="Department ID for permission filtering"
        ),
        FieldSchema(
            name="is_public", dtype=DataType.BOOL,
            description="Whether document is public"
        ),
        FieldSchema(
            name="allowed_roles", dtype=DataType.ARRAY, max_capacity=10,
            element_type=DataType.VARCHAR, max_length=50,
            description="Allowed roles for permission filtering"
        ),
        FieldSchema(
            name="page_number", dtype=DataType.INT64,
            description="Page number"
        ),
        FieldSchema(
            name="section", dtype=DataType.VARCHAR, max_length=100,
            description="Section title"
        ),
        FieldSchema(
            name="chunk_index", dtype=DataType.INT64,
            description="Chunk index in document"
        ),
        FieldSchema(
            name="created_at", dtype=DataType.INT64,
            description="Creation timestamp"
        ),
        FieldSchema(
            name="embedding", dtype=DataType.FLOAT_VECTOR, dim=DIMENSION,
            description="BGE-M3 embedding"
        ),
    ]

    schema = CollectionSchema(
        fields=fields,
        description="Enterprise documents collection",
        enable_dynamic_field=True
    )

    # 创建 Collection
    print(f"正在创建 Collection: {COLLECTION_NAME}")
    client.create_collection(
        collection_name=COLLECTION_NAME,
        schema=schema
    )

    # 创建向量索引 (HNSW)
    print("正在创建索引...")
    index_params = client.prepare_index_params()
    index_params.add_index(
        field_name="embedding",
        index_type="HNSW",
        metric_type="COSINE",
        params={
            "M": 16,
            "efConstruction": 100
        }
    )
    client.create_index(
        collection_name=COLLECTION_NAME,
        index_params=index_params
    )

    # 验证
    collections = client.list_collections()
    print(f"创建成功！当前 Collections: {collections}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="初始化 Milvus Collection")
    parser.add_argument("--overwrite", action="store_true", help="覆盖已存在的 Collection")
    args = parser.parse_args()
    init_milvus(overwrite=args.overwrite)
