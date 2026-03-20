"""
RAG Provider 多实现测试
测试不同 provider 的 retriever 创建和使用
"""
import os
import sys
import io

# 设置stdout编码
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 设置环境变量
os.environ.setdefault("LOG_LEVEL", "WARNING")
os.environ["CUDA_VISIBLE_DEVICES"] = ""


def test_provider_enum():
    """测试1: Provider 枚举定义"""
    print("\n" + "="*60)
    print("测试1: Provider 枚举定义")
    print("="*60)

    try:
        from app.rag.providers import RAGProviderType, RAGProviderConfig

        print(f"✅ Provider枚举导入成功")
        print(f"   可用Provider: {[p.value for p in RAGProviderType]}")

        # 测试配置
        config = RAGProviderConfig(provider=RAGProviderType.CUSTOM, top_k=30)
        print(f"   测试配置: {config.provider.value}, top_k={config.top_k}")

        return True
    except Exception as e:
        print(f"❌ Provider枚举导入失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_factory_custom():
    """测试2: 工厂函数创建 custom retriever"""
    print("\n" + "="*60)
    print("测试2: 工厂函数创建 custom retriever")
    print("="*60)

    try:
        from app.rag.retriever.factory import create_retriever
        from app.rag.retriever.hybrid_retriever import HybridRetriever

        # 测试使用 custom provider
        retriever = create_retriever(provider="custom")

        print(f"✅ Custom retriever 创建成功")
        print(f"   类型: {type(retriever).__name__}")

        return True
    except Exception as e:
        print(f"❌ Custom retriever 创建失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_factory_langchain():
    """测试3: 工厂函数创建 langchain retriever"""
    print("\n" + "="*60)
    print("测试3: 工厂函数创建 langchain retriever")
    print("="*60)

    try:
        from app.rag.retriever.factory import create_retriever, get_available_providers

        # 检查 provider 是否可用
        providers = get_available_providers()
        langchain_provider = next((p for p in providers if p["name"] == "langchain"), None)

        print(f"   LangChain provider 状态: {'可用' if langchain_provider['available'] else '不可用'}")

        if not langchain_provider["available"]:
            print(f"⚠️ LangChain 未安装，跳过测试")
            print(f"   安装命令: pip install langchain langchain-milvus langchain-openai")
            return None

        # 测试创建
        retriever = create_retriever(provider="langchain")

        print(f"✅ LangChain retriever 创建成功")
        print(f"   类型: {type(retriever).__name__}")

        return True
    except ImportError as e:
        print(f"⚠️ LangChain 未安装: {e}")
        return None
    except Exception as e:
        print(f"❌ LangChain retriever 创建失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_factory_llamaindex():
    """测试4: 工厂函数创建 llamaindex retriever"""
    print("\n" + "="*60)
    print("测试4: 工厂函数创建 llamaindex retriever")
    print("="*60)

    try:
        from app.rag.retriever.factory import create_retriever, get_available_providers

        # 检查 provider 是否可用
        providers = get_available_providers()
        llamaindex_provider = next((p for p in providers if p["name"] == "llamaindex"), None)

        print(f"   LlamaIndex provider 状态: {'可用' if llamaindex_provider['available'] else '不可用'}")

        if not llamaindex_provider["available"]:
            print(f"⚠️ LlamaIndex 未安装，跳过测试")
            print(f"   安装命令: pip install llama-index llama-index-vector-stores-milvus")
            return None

        # 测试创建
        retriever = create_retriever(provider="llamaindex")

        print(f"✅ LlamaIndex retriever 创建成功")
        print(f"   类型: {type(retriever).__name__}")

        return True
    except ImportError as e:
        print(f"⚠️ LlamaIndex 未安装: {e}")
        return None
    except Exception as e:
        print(f"❌ LlamaIndex retriever 创建失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_factory_milvus():
    """测试5: 工厂函数创建 milvus hybrid retriever"""
    print("\n" + "="*60)
    print("测试5: 工厂函数创建 milvus hybrid retriever")
    print("="*60)

    try:
        from app.rag.retriever.factory import create_retriever, get_available_providers

        # 检查 provider 是否可用
        providers = get_available_providers()
        milvus_provider = next((p for p in providers if p["name"] == "milvus"), None)

        print(f"   Milvus Hybrid provider 状态: {'可用' if milvus_provider['available'] else '不可用'}")

        # Milvus 应该总是可用的 (依赖 pymilvus)
        retriever = create_retriever(provider="milvus")

        print(f"✅ Milvus Hybrid retriever 创建成功")
        print(f"   类型: {type(retriever).__name__}")

        return True
    except Exception as e:
        print(f"❌ Milvus Hybrid retriever 创建失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_pipeline_with_provider():
    """测试6: RAGPipeline 使用不同 provider"""
    print("\n" + "="*60)
    print("测试6: RAGPipeline 使用不同 provider")
    print("="*60)

    try:
        from app.rag.pipeline import RAGPipeline

        # 测试 custom provider
        pipeline_custom = RAGPipeline(provider="custom")
        print(f"✅ Custom Pipeline 创建成功")
        print(f"   provider: {pipeline_custom.provider}")

        # 测试 langchain provider (如果可用)
        try:
            pipeline_lc = RAGPipeline(provider="langchain")
            print(f"✅ LangChain Pipeline 创建成功")
        except ImportError:
            print(f"⚠️ LangChain Pipeline 跳过 (未安装)")

        # 测试 llamaindex provider (如果可用)
        try:
            pipeline_li = RAGPipeline(provider="llamaindex")
            print(f"✅ LlamaIndex Pipeline 创建成功")
        except ImportError:
            print(f"⚠️ LlamaIndex Pipeline 跳过 (未安装)")

        # 测试 milvus provider
        pipeline_mv = RAGPipeline(provider="milvus")
        print(f"✅ Milvus Pipeline 创建成功")

        return True
    except Exception as e:
        print(f"❌ Pipeline 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_retrieval_custom():
    """测试7: Custom Provider 检索测试"""
    print("\n" + "="*60)
    print("测试7: Custom Provider 检索测试")
    print("="*60)

    try:
        from app.rag.retriever.factory import create_retriever
        import asyncio

        retriever = create_retriever(provider="custom")

        print(f"🔍 执行检索测试...")

        async def run():
            results = await retriever.retrieve(
                query="abstract",
                top_k=5
            )
            return results

        results = asyncio.run(run())

        print(f"✅ 检索成功!")
        print(f"   返回结果数: {len(results)}")

        if results:
            print(f"   第一个结果:")
            print(f"   - ID: {results[0].chunk_id}")
            print(f"   - 分数: {results[0].score:.4f}")
            print(f"   - 内容: {results[0].content[:100]}...")

        return results
    except Exception as e:
        print(f"❌ 检索测试失败: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_get_available_providers():
    """测试8: 获取所有可用 providers"""
    print("\n" + "="*60)
    print("测试8: 获取所有可用 providers")
    print("="*60)

    try:
        from app.rag.retriever.factory import get_available_providers

        providers = get_available_providers()

        print(f"✅ 获取 providers 成功")
        print(f"   可用 providers 数量: {len(providers)}")

        for p in providers:
            status = "✅" if p["available"] else "❌"
            print(f"   {status} {p['name']}: {p['display_name']}")
            print(f"      {p['description']}")

        return True
    except Exception as e:
        print(f"❌ 获取 providers 失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主函数"""
    print("\n" + "#"*60)
    print("# RAG Provider 多实现测试")
    print("#"*60)

    tests = [
        ("Provider枚举", test_provider_enum),
        ("Factory Custom", test_factory_custom),
        ("Factory LangChain", test_factory_langchain),
        ("Factory LlamaIndex", test_factory_llamaindex),
        ("Factory Milvus", test_factory_milvus),
        ("Pipeline with Provider", test_pipeline_with_provider),
        ("Retrieval Custom", test_retrieval_custom),
        ("Get Available Providers", test_get_available_providers),
    ]

    results = []
    for test_name, test_func in tests:
        result = test_func()
        results.append((test_name, result))

    # 总结
    print("\n" + "#"*60)
    print("# 测试总结")
    print("#"*60)

    passed = 0
    failed = 0
    skipped = 0

    for test_name, result in results:
        if result is True:
            status = "✅"
            passed += 1
        elif result is None:
            status = "⏭️"
            skipped += 1
        else:
            status = "❌"
            failed += 1
        print(f"   {status} {test_name}")

    print(f"\n   总计: {passed} 通过, {failed} 失败, {skipped} 跳过")

    if failed == 0:
        print("\n🎉 所有测试通过!")
    else:
        print("\n⚠️ 部分测试失败，请检查上述错误信息。")


if __name__ == "__main__":
    main()
