"""
RAG端到端测试脚本
测试完整的RAG流程: 解析 -> 分块 -> Embedding -> 检索 -> Rerank -> 生成
"""
import os
import sys
import io

# 设置stdout编码为utf-8，避免emoji打印问题
# line_buffering=True 禁用缓冲，确保输出立即显示
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True)

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 设置环境变量，禁用一些可能有问题的模块
os.environ.setdefault("LOG_LEVEL", "WARNING")

# 强制使用CPU运行（当前环境无GPU）
os.environ["CUDA_VISIBLE_DEVICES"] = ""


def test_1_parse_pdf():
    """测试1: PDF解析"""
    print("\n" + "="*60)
    print("测试1: PDF解析")
    print("="*60)

    from app.processors.parser import DocumentParser

    pdf_path = os.path.join(
        os.path.dirname(__file__),
        "files",
        "1911.05722v3.pdf"
    )

    if not os.path.exists(pdf_path):
        print(f"❌ PDF文件不存在: {pdf_path}")
        return None

    print(f"📄 解析PDF: {pdf_path}")

    try:
        result = DocumentParser.parse(pdf_path, "pdf")
        print(f"✅ PDF解析成功!")
        print(f"   - 页数: {result['metadata'].get('page_count', 'N/A')}")
        print(f"   - 内容长度: {len(result['content'])} 字符")
        print(f"   - 内容预览 (前300字符):")
        print(f"   {result['content'][:300]}...")
        return result
    except Exception as e:
        print(f"❌ PDF解析失败: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_2_chunking(parse_result):
    """测试2: 文档分块"""
    print("\n" + "="*60)
    print("测试2: 文档分块")
    print("="*60)

    if not parse_result:
        print("❌ 跳过 (parse_result为空)")
        return None

    from app.processors.chunker import chunk_document

    document_id = "test_doc_001"

    print(f"📦 对文档进行分块 (策略: fixed)")

    try:
        chunks = chunk_document(
            document_id=document_id,
            content=parse_result["content"],
            pages=parse_result.get("pages", []),
            strategy="fixed",
            chunk_size=512,
            chunk_overlap=50
        )

        print(f"✅ 分块成功!")
        print(f"   - 生成chunks数量: {len(chunks)}")

        if chunks:
            # 显示前3个chunk的预览
            for i, chunk in enumerate(chunks[:3]):
                print(f"\n   Chunk {i+1} (长度: {len(chunk['content'])} 字符):")
                print(f"   {chunk['content'][:150]}...")

        return chunks
    except Exception as e:
        print(f"❌ 分块失败: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_3_embedding(chunks):
    """测试3: Embedding向量化"""
    print("\n" + "="*60)
    print("测试3: Embedding向量化")
    print("="*60)

    if not chunks:
        print("❌ 跳过 (chunks为空)")
        return None

    from app.rag.embedding import encode_text

    print(f"🔢 对 {len(chunks)} 个chunks进行embedding...")

    try:
        chunk_texts = [c["content"] for c in chunks]
        embeddings = encode_text(chunk_texts)

        print(f"✅ Embedding成功!")
        print(f"   - Embedding维度: {len(embeddings[0]) if embeddings else 'N/A'}")
        print(f"   - Embedding形状: ({len(embeddings)}, {len(embeddings[0]) if embeddings else 0})")

        # 显示部分embedding值
        if embeddings and len(embeddings[0]) > 0:
            print(f"   - 第一个embedding前5个值: {embeddings[0][:5]}")

        return embeddings
    except Exception as e:
        print(f"❌ Embedding失败: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_4_milvus_connection():
    """测试4: Milvus连接"""
    print("\n" + "="*60)
    print("测试4: Milvus连接")
    print("="*60)

    from app.config import settings

    print(f"🔌 尝试连接Milvus...")
    print(f"   - Host: {settings.MILVUS_HOST}")
    print(f"   - Port: {settings.MILVUS_PORT}")
    print(f"   - Collection: {settings.MILVUS_COLLECTION_NAME}")
    print(f"   - 云模式: {bool(settings.MILVUS_CLOUD_URI)}")

    try:
        from app.integrations.milvus_client import get_milvus_client

        client = get_milvus_client()
        client.connect()

        health = client.check_health()
        print(f"   - 健康状态: {health}")

        if "unhealthy" in health.lower():
            print(f"❌ Milvus连接失败: {health}")
            return None

        print(f"✅ Milvus连接成功!")
        return client
    except Exception as e:
        print(f"❌ Milvus连接失败: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_5_meilisearch_connection():
    """测试5: Meilisearch连接"""
    print("\n" + "="*60)
    print("测试5: Meilisearch连接")
    print("="*60)

    from app.config import settings

    print(f"🔌 尝试连接Meilisearch...")
    print(f"   - URL: {settings.MEILISEARCH_URL}")
    print(f"   - Index: {settings.MEILISEARCH_INDEX_NAME}")

    try:
        from app.integrations.search_engine import get_meilisearch_client

        client = get_meilisearch_client()
        client.connect()

        health = client.check_health()
        print(f"   - 健康状态: {health}")

        if "unhealthy" in health.lower():
            print(f"❌ Meilisearch连接失败: {health}")
            return None

        print(f"✅ Meilisearch连接成功!")
        return client
    except Exception as e:
        print(f"❌ Meilisearch连接失败: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_6_hybrid_retrieval(chunks, embeddings):
    """测试6: 混合检索"""
    print("\n" + "="*60)
    print("测试6: 混合检索")
    print("="*60)

    if not chunks or not embeddings:
        print("❌ 跳过 (chunks或embeddings为空)")
        return None

    try:
        from app.integrations.milvus_client import get_milvus_client
        from app.integrations.search_engine import get_meilisearch_client
        from app.rag.retriever.hybrid_retriever import HybridRetriever
        import asyncio

        milvus_client = get_milvus_client()
        meilisearch_client = get_meilisearch_client()

        # 先插入测试数据
        print(f"📤 插入测试数据到向量数据库...")

        document_id = "test_doc_001"
        milvus_data = []
        search_data = []

        # 兼容 numpy array 和 list
        embedding_list = embeddings.tolist() if hasattr(embeddings, 'tolist') else embeddings
        for idx, (chunk_data, embedding) in enumerate(zip(chunks, embedding_list)):
            milvus_data.append({
                "chunk_id": chunk_data["chunk_id"],
                "document_id": document_id,
                "content": chunk_data["content"],
                "title": "测试文档",
                "department_id": None,
                "is_public": True,
                "allowed_roles": [],
                "page_number": chunk_data.get("page_number"),
                "section": chunk_data.get("section"),
                "chunk_index": chunk_data["chunk_index"],
                "embedding": embedding,
            })

            search_data.append({
                "chunk_id": chunk_data["chunk_id"],
                "document_id": document_id,
                "content": chunk_data["content"],
                "title": "测试文档",
                "department_id": None,
                "is_public": True,
                "allowed_roles": [],
                "page_number": chunk_data.get("page_number"),
                "section": chunk_data.get("section"),
                "chunk_index": chunk_data["chunk_index"],
                "created_at": 0,
            })

        # 插入Milvus
        try:
            milvus_ids = milvus_client.insert_chunks(milvus_data)
            print(f"   - Milvus插入成功: {len(milvus_ids)} 条")
        except Exception as e:
            print(f"   ⚠️ Milvus插入失败: {e}")
            # 继续测试，即使Milvus插入失败

        # 插入Meilisearch
        try:
            meilisearch_client.add_documents(search_data)
            print(f"   - Meilisearch插入成功: {len(search_data)} 条")
        except Exception as e:
            print(f"   ⚠️ Meilisearch插入失败: {e}")
            # 继续测试

        # 执行检索测试
        print(f"\n🔍 执行检索测试...")

        test_query = "abstract"

        retriever = HybridRetriever(
            vector_top_k=5,
            bm25_top_k=5,
            fusion_k=10
        )

        async def run_retrieval():
            return await retriever.retrieve(
                query=test_query,
                top_k=5
            )

        results = asyncio.run(run_retrieval())

        print(f"✅ 检索成功!")
        print(f"   - 查询: '{test_query}'")
        print(f"   - 返回结果数: {len(results)}")

        for i, result in enumerate(results[:3]):
            print(f"\n   结果 {i+1}:")
            print(f"   - ID: {result.chunk_id}")
            print(f"   - 分数: {result.score:.4f}")
            print(f"   - 内容: {result.content[:100]}...")

        return results

    except Exception as e:
        print(f"❌ 混合检索失败: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_7_reranker():
    """测试7: Reranker"""
    print("\n" + "="*60)
    print("测试7: Reranker")
    print("="*60)

    try:
        from app.rag.reranker.bge_reranker import get_reranker

        print(f"🔄 加载Reranker模型...")

        reranker = get_reranker()

        # 测试rerank
        test_docs = [
            {"id": "1", "content": "机器学习是人工智能的一个分支"},
            {"id": "2", "content": "今天天气很好，适合出去游玩"},
            {"id": "3", "content": "深度学习在计算机视觉领域应用广泛"},
        ]

        query = "深度学习在视觉领域的应用"

        print(f"   - 查询: '{query}'")

        reranked = reranker.rerank(query, test_docs, top_k=3)

        print(f"✅ Rerank成功!")
        print(f"   - 返回结果数: {len(reranked)}")

        for i, doc in enumerate(reranked):
            print(f"\n   结果 {i+1} (rerank_score: {doc.get('rerank_score', 'N/A'):.4f}):")
            print(f"   - ID: {doc['id']}")
            print(f"   - 内容: {doc['content']}")

        return reranked

    except Exception as e:
        print(f"❌ Reranker失败: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_8_full_pipeline():
    """测试8: 完整Pipeline (不含LLM)"""
    print("\n" + "="*60)
    print("测试8: 完整Pipeline (不含LLM)")
    print("="*60)

    try:
        from app.rag.pipeline import RAGPipeline
        from app.rag.retriever.hybrid_retriever import HybridRetriever
        from pydantic import BaseModel

        # 创建一个简单的用户对象
        class MockUser(BaseModel):
            id: str = "test_user"
            department_id: str = None
            name: str = "Test User"

        user = MockUser()

        print(f"🤖 初始化RAG Pipeline...")

        pipeline = RAGPipeline(
            top_k=5,
            reranker_top_k=3,
            min_score=0.3,
            max_context_tokens=2000
        )

        print(f"✅ Pipeline初始化成功!")
        print(f"   - top_k: {pipeline.top_k}")
        print(f"   - reranker_top_k: {pipeline.reranker_top_k}")
        print(f"   - min_score: {pipeline.min_score}")

        return pipeline

    except Exception as e:
        print(f"❌ Pipeline初始化失败: {e}")
        import traceback
        traceback.print_exc()
        return None


def cleanup_test_data():
    """清理测试数据"""
    print("\n" + "="*60)
    print("清理测试数据")
    print("="*60)

    try:
        from app.integrations.milvus_client import get_milvus_client
        from app.integrations.search_engine import get_meilisearch_client

        milvus_client = get_milvus_client()
        meilisearch_client = get_meilisearch_client()

        # 删除测试文档
        try:
            milvus_client.delete_by_document("test_doc_001")
            print(f"✅ Milvus测试数据已清理")
        except Exception as e:
            print(f"⚠️ Milvus清理失败: {e}")

        try:
            meilisearch_client.delete_by_document("test_doc_001")
            print(f"✅ Meilisearch测试数据已清理")
        except Exception as e:
            print(f"⚠️ Meilisearch清理失败: {e}")

    except Exception as e:
        print(f"⚠️ 清理过程出错: {e}")


def main():
    """主函数"""
    print("\n" + "#"*60)
    print("# RAG端到端测试")
    print("#"*60)

    # 测试1: PDF解析
    parse_result = test_1_parse_pdf()

    # 测试2: 分块
    chunks = test_2_chunking(parse_result)

    # 测试3: Embedding
    embeddings = test_3_embedding(chunks)

    # 测试4: Milvus连接
    milvus_client = test_4_milvus_connection()

    # 测试5: Meilisearch连接
    meilisearch_client = test_5_meilisearch_connection()

    # 测试6: 混合检索
    if milvus_client and meilisearch_client:
        retrieval_results = test_6_hybrid_retrieval(chunks, embeddings)
    else:
        retrieval_results = None

    # 测试7: Reranker
    rerank_results = test_7_reranker()

    # 测试8: 完整Pipeline
    pipeline = test_8_full_pipeline()

    # 清理
    cleanup_test_data()

    # 总结
    print("\n" + "#"*60)
    print("# 测试总结")
    print("#"*60)

    tests = [
        ("PDF解析", parse_result is not None),
        ("文档分块", chunks is not None and len(chunks) > 0),
        ("Embedding", embeddings is not None and len(embeddings) > 0),
        ("Milvus连接", milvus_client is not None),
        ("Meilisearch连接", meilisearch_client is not None),
        ("混合检索", retrieval_results is not None and len(retrieval_results) > 0),
        ("Reranker", rerank_results is not None and len(rerank_results) > 0),
        ("Pipeline", pipeline is not None),
    ]

    passed = 0
    failed = 0

    for test_name, result in tests:
        status = "✅" if result else "❌"
        print(f"   {status} {test_name}")
        if result:
            passed += 1
        else:
            failed += 1

    print(f"\n   总计: {passed} 通过, {failed} 失败")

    if failed == 0:
        print("\n🎉 所有测试通过! RAG核心流程可以正常运行.")
    else:
        print("\n⚠️ 部分测试失败, 请检查上述错误信息.")


if __name__ == "__main__":
    main()
