"""
Check Milvus Collection status
"""
from pymilvus import MilvusClient

CLOUD_URI = "https://in03-d3a0c989c183420.serverless.ali-cn-hangzhou.cloud.zilliz.com.cn"
TOKEN = "cb3fe251c781690585cc11f3f99cdb53dd6067ce4c2e37531ddb4dccdc480794237ee5929ecf8cff7fa361b7ba7015064ff89725"

client = MilvusClient(uri=CLOUD_URI, token=TOKEN)
collections = client.list_collections()
print("Collections:", collections)

if "enterprise_documents" in collections:
    print("Collection exists!")
    # Get info
    stats = client.get_collection_stats("enterprise_documents")
    print("Stats:", stats)
