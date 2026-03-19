import asyncio
import sys
sys.path.insert(0, '.')

async def test():
    # 创建一个简单的 MockUser
    class MockUser:
        def __init__(self):
            self.id = "test-user-id"
            self.department_id = None
            self.roles = []

    from app.rag.pipeline import RAGPipeline
    from app.integrations.llm_server import get_llm_client
    from app.integrations.milvus_client import get_milvus_client

    # 创建 pipeline
    pipeline = RAGPipeline(
        vector_client=get_milvus_client(),
        search_client=None,
        llm_client=get_llm_client()
    )

    # 直接调用 LLM
    user = MockUser()
    result = await pipeline.query(
        query="hello",
        user=user
    )

    print("Answer:", result.answer)
    print("Sources:", result.sources)

asyncio.run(test())
