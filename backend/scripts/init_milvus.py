"""
Milvus Collection 初始化脚本
用于全新的 Milvus 集群创建 Collection 和索引
"""
import sys
sys.path.insert(0, 'd:/Learning/EnterpriseKB/backend')

from app.integrations.milvus_client import get_milvus_client


def init_milvus(overwrite: bool = False):
    """
    初始化 Milvus Collection

    Args:
        overwrite: 是否覆盖已存在的 Collection
    """
    client = get_milvus_client()

    # 检查是否已存在
    if client.client.has_collection(client.collection_name):
        if overwrite:
            print(f"删除已存在的 Collection: {client.collection_name}")
            client.drop_collection()
        else:
            print(f"Collection {client.collection_name} 已存在，跳过创建")
            return

    # 创建 Collection 和索引
    print(f"正在创建 Collection: {client.collection_name}")
    client.create_collection()

    # 验证
    collections = client.client.list_collections()
    print(f"创建成功！当前 Collections: {collections}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="初始化 Milvus Collection")
    parser.add_argument("--overwrite", action="store_true", help="覆盖已存在的 Collection")
    args = parser.parse_args()

    init_milvus(overwrite=args.overwrite)
