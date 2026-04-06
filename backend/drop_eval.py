from app.integrations.milvus_client import MilvusClientWrapper

milvus = MilvusClientWrapper(collection_name='evaluation')
milvus.connect()

if milvus.client.has_collection('evaluation'):
    print('Dropping evaluation collection...')
    milvus.client.drop_collection('evaluation')
    print('Done')
else:
    print('Collection does not exist')
