import asyncio
import sys
sys.path.insert(0, '.')
from app.integrations.llm_server import get_llm_client

async def test():
    client = get_llm_client()
    messages = [
        {'role': 'user', 'content': 'hello'}
    ]
    result = await client.generate(messages)
    print(result)

asyncio.run(test())
