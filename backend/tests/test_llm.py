"""测试 MiniMax LLM 客户端"""
import asyncio
import sys
sys.path.insert(0, '.')

from app.integrations.llm_server import get_llm_client


async def test_llm():
    client = get_llm_client()

    print(f"Provider: {client.provider}")
    print(f"API URL: {client.api_url}")
    print(f"Model: {client.model_name}")
    print(f"API Key: {client.api_key[:20]}..." if client.api_key else "API Key: None")

    # 检查健康状态
    print("\n检查服务状态...")
    health = await client.check_health()
    print(f"Health: {health}")

    # 测试生成
    print("\n测试生成...")
    messages = [
        {"role": "system", "content": ""},
        {"role": "user", "content": "你是什么模型？"}
    ]

    try:
        response = await client.generate(messages, max_tokens=200)
        print(f"Response: {response}")
        print("\n✅ LLM 客户端测试成功!")
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")


if __name__ == "__main__":
    asyncio.run(test_llm())
