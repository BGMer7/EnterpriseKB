"""
召回率测试脚本 V2
使用真实的 RAG 模块组件，但独立的 evaluation collection
"""
import os
import sys
import io
import json
import asyncio
import time
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from pathlib import Path

# 设置 stdout 编码
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True)

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入真实的 RAG 组件
from app.integrations.milvus_client import MilvusClientWrapper
from app.integrations.search_engine import get_meilisearch_client
from app.rag.retriever.vector_retriever import VectorRetriever
from app.rag.retriever.bm25_retriever import BM25Retriever
from app.rag.retriever.hybrid_retriever import HybridRetriever
from app.rag.embedding import encode_text, encode_query
from app.processors.chunker import chunk_by_strategy


# ===== 配置 =====
EVAL_COLLECTION_NAME = "evaluation"  # 独立的 evaluation collection
MARKDOWN_DIR = "src/static/miner_output"
GROUND_TRUTH_PATH = "tests/results/ground_truth_v2.json"


@dataclass
class TestCase:
    """测试用例"""
    question: str
    relevant_docs: List[str]
    relevant_chunk_ids: List[str] = None
    ground_truth: str = ""


def load_markdown_files(directory: str) -> Dict[str, tuple]:
    """加载 Markdown 文件"""
    docs = {}
    dir_path = Path(directory)

    if not dir_path.exists():
        print(f"❌ 目录不存在: {directory}")
        return docs

    for md_file in dir_path.glob("*.md"):
        try:
            with open(md_file, "r", encoding="utf-8") as f:
                content = f.read()
                doc_name = md_file.stem.replace("MinerU_markdown_", "")
                title = doc_name
                docs[doc_name] = (title, content)
                print(f"  ✓ 加载: {md_file.name} ({len(content)} 字符)")
        except Exception as e:
            print(f"  ✗ 加载失败 {md_file.name}: {e}")

    print(f"\n📚 总计加载: {len(docs)} 个文档")
    return docs


def chunk_documents(docs: Dict[str, tuple]) -> List[Dict]:
    """使用 Markdown 结构化分块"""
    print("\n[分块] 使用 Markdown 结构化分块...")

    all_chunks = []
    for doc_id, (title, content) in docs.items():
        pages = [{"page_number": 1, "content": content}]

        # 使用 markdown 分块策略
        chunks = chunk_by_strategy(
            document_id=doc_id,
            content=content,
            pages=pages,
            strategy="markdown",
            chunk_size=512,
            chunk_overlap=64
        )

        for chunk in chunks:
            all_chunks.append({
                "chunk_id": chunk["chunk_id"],
                "document_id": chunk["document_id"],
                "content": chunk["content"],
                "title": title,
                "chunk_index": chunk["chunk_index"],
                "page_number": chunk.get("page_number", 1),
                "section": chunk.get("section", ""),
            })
        print(f"  - {doc_id}: {len(chunks)} chunks")

    print(f"\n📦 总计 chunks: {len(all_chunks)}")
    return all_chunks


def init_evaluation_collection(chunks: List[Dict], recreate: bool = True):
    """初始化 evaluation collection，插入数据"""
    print(f"\n[Milvus] 初始化 evaluation collection...")

    # 创建独立 client（使用 evaluation collection）
    milvus = MilvusClientWrapper(collection_name=EVAL_COLLECTION_NAME)
    milvus.connect()

    # 检查是否需要重建
    if milvus.client.has_collection(EVAL_COLLECTION_NAME):
        if recreate:
            print(f"  - 删除旧 collection")
            milvus.client.drop_collection(EVAL_COLLECTION_NAME)
        else:
            print(f"  - 使用已有 collection")
            return milvus

    # 创建 collection（复用原有 schema，但使用实际 embedding 维度）
    print(f"  - 创建 collection: {EVAL_COLLECTION_NAME}")

    # 先获取一个 embedding 确定维度
    sample_embedding = encode_text([chunks[0]["content"]])[0]
    actual_dim = len(sample_embedding)
    print(f"  - 向量维度: {actual_dim}")

    milvus.dimension = actual_dim
    milvus.create_collection(overwrite=True)

    # 批量向量化并插入
    print(f"  - 向量化 {len(chunks)} 个 chunks...")
    texts = [c["content"] for c in chunks]
    embeddings = encode_text(texts)
    embeddings_list = embeddings.tolist() if hasattr(embeddings, 'tolist') else embeddings

    # 准备 Milvus 数据
    milvus_data = []
    for chunk, embedding in zip(chunks, embeddings_list):
        milvus_data.append({
            "chunk_id": chunk["chunk_id"],
            "document_id": chunk["document_id"],
            "content": chunk["content"],
            "title": chunk["title"],
            "department_id": "",
            "is_public": True,
            "allowed_roles": [],
            "page_number": chunk.get("page_number") or 1,  # 默认为 1
            "section": chunk.get("section") or "",
            "chunk_index": chunk.get("chunk_index") or 0,
            "created_at": int(time.time()),
            "embedding": embedding,
        })

    # 插入
    print(f"  - 插入 Milvus...")
    milvus.insert_chunks(milvus_data)
    print(f"  ✓ 完成")

    return milvus


def init_meilisearch_index(chunks: List[Dict], recreate: bool = True):
    """初始化 Meilisearch 索引"""
    print(f"\n[Meilisearch] 初始化索引...")

    meili = get_meilisearch_client()
    index_name = "evaluation"

    # 检查是否需要重建
    try:
        indexes = meili.client.get_indexes()
        index_names = [idx.uid for idx in indexes.get("results", [])]

        if index_name in index_names and recreate:
            print(f"  - 删除旧索引")
            meili.client.delete_index(index_name)
    except Exception as e:
        print(f"  - 检查索引时出错: {e}")

    # 准备数据
    search_data = []
    for chunk in chunks:
        search_data.append({
            "id": chunk["chunk_id"],
            "chunk_id": chunk["chunk_id"],
            "document_id": chunk["document_id"],
            "content": chunk["content"],
            "title": chunk["title"],
            "department_id": "",
            "is_public": True,
            "allowed_roles": [],
            "page_number": chunk.get("page_number") or 1,
            "section": chunk.get("section") or "",
            "chunk_index": chunk.get("chunk_index") or 0,
            "created_at": int(time.time()),
        })

    # 添加文档
    try:
        meili.add_documents(search_data, index_name=index_name)
        print(f"  ✓ 插入 {len(search_data)} 条文档")
    except Exception as e:
        print(f"  ⚠️ Meilisearch 插入失败: {e}")
        print(f"     跳过 BM25 测试")
        return None

    return index_name


def load_ground_truth(path: str) -> List[TestCase]:
    """加载 ground truth 数据"""
    print(f"\n[Ground Truth] 加载: {path}")

    if not Path(path).exists():
        print(f"  ❌ 文件不存在")
        return []

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    cases = []
    for item in data.get("chunk_level", []):
        cases.append(TestCase(
            question=item["question"],
            relevant_docs=item.get("relevant_doc_ids", []),
            relevant_chunk_ids=item.get("relevant_chunk_ids", []),
            ground_truth=item.get("ground_truth", "")
        ))

    print(f"  ✓ 加载 {len(cases)} 个测试用例")
    return cases


def calculate_metrics(retrieved_ids: List[str], relevant_ids: List[str], top_k: int) -> Dict:
    """计算评估指标"""
    if not relevant_ids:
        return {"hit": 0, "recall": 0.0, "precision": 0.0, "mrr": 0.0}

    retrieved_k = retrieved_ids[:top_k]

    # Hit Rate
    hit = int(any(rid in relevant_ids for rid in retrieved_k))

    # Recall
    recalled = len(set(retrieved_k) & set(relevant_ids))
    recall = recalled / len(relevant_ids)

    # Precision
    precision = recalled / top_k

    # MRR
    mrr = 0.0
    for rank, rid in enumerate(retrieved_k, 1):
        if rid in relevant_ids:
            mrr = 1.0 / rank
            break

    return {
        "hit": hit,
        "recall": round(recall, 4),
        "precision": round(precision, 4),
        "mrr": round(mrr, 4)
    }


async def evaluate_vector(test_cases: List[TestCase], top_k: int = 5) -> Dict:
    """评估向量检索"""
    print(f"\n[评估] 向量检索 (Milvus)...")

    # 直接使用 evaluation collection 的 client
    milvus = MilvusClientWrapper(collection_name=EVAL_COLLECTION_NAME)
    client = milvus.connect()

    # 确保 collection 已加载（使用 client API）
    if client.get_load_state(EVAL_COLLECTION_NAME) != "Loaded":
        client.load_collection(EVAL_COLLECTION_NAME)

    results = []
    for i, case in enumerate(test_cases, 1):
        # 编码查询
        query_embedding = encode_query(case.question)

        # 直接搜索
        search_results = milvus.search(
            query_embedding=query_embedding,
            top_k=top_k
        )

        retrieved_ids = [r["chunk_id"] for r in search_results]

        metrics = calculate_metrics(retrieved_ids, case.relevant_chunk_ids or [], top_k)

        results.append({
            "question": case.question,
            "retrieved": retrieved_ids,
            "relevant": case.relevant_chunk_ids,
            "metrics": metrics,
            "top_results": [
                {
                    "chunk_id": r["chunk_id"],
                    "document_id": r["document_id"],
                    "score": round(r["score"], 4),
                    "content_preview": r["content"][:100] + "..." if len(r["content"]) > 100 else r["content"]
                }
                for r in search_results[:3]
            ]
        })

        if i % 10 == 0 or i == len(test_cases):
            print(f"  进度: {i}/{len(test_cases)}")

    # 汇总
    avg_metrics = {
        "hit_rate": round(sum(r["metrics"]["hit"] for r in results) / len(results), 4),
        "recall": round(sum(r["metrics"]["recall"] for r in results) / len(results), 4),
        "precision": round(sum(r["metrics"]["precision"] for r in results) / len(results), 4),
        "mrr": round(sum(r["metrics"]["mrr"] for r in results) / len(results), 4),
    }

    return {"method": "vector", "avg_metrics": avg_metrics, "results": results}


async def evaluate_bm25(test_cases: List[TestCase], index_name: str, top_k: int = 5) -> Optional[Dict]:
    """评估 BM25 检索"""
    if not index_name:
        return None

    print(f"\n[评估] BM25 检索 (Meilisearch)...")

    # 临时修改 Meilisearch index 名称
    from app import integrations
    original_get_meili = integrations.search_engine.get_meilisearch_client

    class EvalMeilisearchClient:
        def __init__(self, original):
            self._original = original

        def search(self, query: str, limit: int = 10, filter_expression: str = None):
            # 使用 evaluation index
            return self._original.search(query, limit=limit, filter_expression=filter_expression, index_name=index_name)

        def build_permission_filter(self, department_id, roles):
            return self._original.build_permission_filter(department_id, roles)

    def get_eval_meili():
        return EvalMeilisearchClient(original_get_meili())

    integrations.search_engine.get_meilisearch_client = get_eval_meili

    retriever = BM25Retriever(top_k=top_k * 2)

    results = []
    for i, case in enumerate(test_cases, 1):
        try:
            retrieved = await retriever.retrieve(case.question, top_k=top_k)
            retrieved_ids = [r.chunk_id for r in retrieved]

            metrics = calculate_metrics(retrieved_ids, case.relevant_chunk_ids or [], top_k)

            results.append({
                "question": case.question,
                "retrieved": retrieved_ids,
                "relevant": case.relevant_chunk_ids,
                "metrics": metrics,
            })
        except Exception as e:
            print(f"  查询失败: {e}")
            results.append({
                "question": case.question,
                "retrieved": [],
                "relevant": case.relevant_chunk_ids,
                "metrics": {"hit": 0, "recall": 0, "precision": 0, "mrr": 0},
            })

        if i % 10 == 0 or i == len(test_cases):
            print(f"  进度: {i}/{len(test_cases)}")

    # 恢复
    integrations.search_engine.get_meilisearch_client = original_get_meili

    avg_metrics = {
        "hit_rate": round(sum(r["metrics"]["hit"] for r in results) / len(results), 4),
        "recall": round(sum(r["metrics"]["recall"] for r in results) / len(results), 4),
        "precision": round(sum(r["metrics"]["precision"] for r in results) / len(results), 4),
        "mrr": round(sum(r["metrics"]["mrr"] for r in results) / len(results), 4),
    }

    return {"method": "bm25", "avg_metrics": avg_metrics, "results": results}


async def evaluate_hybrid(test_cases: List[TestCase], top_k: int = 5) -> Optional[Dict]:
    """评估混合检索"""
    print(f"\n[评估] 混合检索 (RRF)...")

    # 需要同时 patch Milvus 和 Meilisearch
    from app import integrations
    original_get_milvus = integrations.milvus_client.get_milvus_client
    original_get_meili = integrations.search_engine.get_meilisearch_client

    def get_eval_milvus():
        return MilvusClientWrapper(collection_name=EVAL_COLLECTION_NAME)

    class EvalMeilisearchClient:
        def __init__(self, original):
            self._original = original

        def search(self, query: str, limit: int = 10, filter_expression: str = None):
            return self._original.search(query, limit=limit, filter_expression=filter_expression, index_name="evaluation")

        def build_permission_filter(self, department_id, roles):
            return self._original.build_permission_filter(department_id, roles)

    def get_eval_meili():
        return EvalMeilisearchClient(original_get_meili())

    integrations.milvus_client.get_milvus_client = get_eval_milvus
    integrations.search_engine.get_meilisearch_client = get_eval_meili

    retriever = HybridRetriever(
        vector_top_k=top_k * 2,
        bm25_top_k=top_k * 2,
        fusion_k=60,
        alpha=0.5
    )

    results = []
    for i, case in enumerate(test_cases, 1):
        try:
            # 使用无权限版本
            retrieved = await retriever.retrieve(case.question, top_k=top_k)
            retrieved_ids = [r.chunk_id for r in retrieved]

            metrics = calculate_metrics(retrieved_ids, case.relevant_chunk_ids or [], top_k)

            results.append({
                "question": case.question,
                "retrieved": retrieved_ids,
                "relevant": case.relevant_chunk_ids,
                "metrics": metrics,
            })
        except Exception as e:
            print(f"  查询失败: {e}")
            import traceback
            traceback.print_exc()
            results.append({
                "question": case.question,
                "retrieved": [],
                "relevant": case.relevant_chunk_ids,
                "metrics": {"hit": 0, "recall": 0, "precision": 0, "mrr": 0},
            })

        if i % 10 == 0 or i == len(test_cases):
            print(f"  进度: {i}/{len(test_cases)}")

    # 恢复
    integrations.milvus_client.get_milvus_client = original_get_milvus
    integrations.search_engine.get_meilisearch_client = original_get_meili

    avg_metrics = {
        "hit_rate": round(sum(r["metrics"]["hit"] for r in results) / len(results), 4),
        "recall": round(sum(r["metrics"]["recall"] for r in results) / len(results), 4),
        "precision": round(sum(r["metrics"]["precision"] for r in results) / len(results), 4),
        "mrr": round(sum(r["metrics"]["mrr"] for r in results) / len(results), 4),
    }

    return {"method": "hybrid", "avg_metrics": avg_metrics, "results": results}


def print_results(vector_result: Dict, bm25_result: Optional[Dict], hybrid_result: Optional[Dict], top_k: int):
    """打印对比结果"""
    print("\n" + "=" * 80)
    print("评估结果对比")
    print("=" * 80)

    print(f"\n📊 平均指标对比 (Top-{top_k}):")
    print("-" * 70)
    print(f"{'方法':<15} {'HitRate@'+str(top_k):<15} {'Recall@'+str(top_k):<15} {'Precision@'+str(top_k):<15} {'MRR':<15}")
    print("-" * 70)

    methods = [
        ("向量检索", vector_result),
        ("BM25", bm25_result),
        ("混合检索", hybrid_result),
    ]

    for name, result in methods:
        if result:
            m = result["avg_metrics"]
            print(f"{name:<15} {m['hit_rate']:<15.4f} {m['recall']:<15.4f} {m['precision']:<15.4f} {m['mrr']:<15.4f}")
        else:
            print(f"{name:<15} {'N/A':<15} {'N/A':<15} {'N/A':<15} {'N/A':<15}")

    print("-" * 70)

    # 打印每个问题的详细检索结果（使用向量检索结果）
    if vector_result and vector_result.get("results"):
        print(f"\n📋 每个问题的检索详情 (向量检索):")
        print("=" * 80)

        for i, r in enumerate(vector_result["results"], 1):
            question = r["question"]
            relevant = r["relevant"]
            metrics = r["metrics"]
            top_results = r.get("top_results", [])

            print(f"\n[{i}] 问题: {question[:60]}...")
            print(f"    相关 chunk: {relevant}")
            print(f"    命中: {'✓' if metrics['hit'] else '✗'} | Recall: {metrics['recall']:.2f} | Precision: {metrics['precision']:.2f}")
            print(f"    检索结果 (Top {top_k}):")

            for j, tr in enumerate(top_results, 1):
                is_relevant = "🎯" if tr["chunk_id"] in relevant else "  "
                score_str = f"[{tr['score']:.3f}]" if tr.get("score") else ""
                content_preview = tr.get("content_preview", "")[:80].replace("\n", " ")
                print(f"      {is_relevant} {j}. {tr['chunk_id']} {score_str}")
                print(f"          {content_preview}...")

            print("-" * 80)


async def main():
    """主流程"""
    import argparse

    parser = argparse.ArgumentParser(description="RAG 召回率测试 V2")
    parser.add_argument("--mode", choices=["all", "vector", "bm25", "hybrid"], default="all",
                        help="测试模式: all=全部, vector=仅向量, bm25=仅BM25, hybrid=仅混合")
    parser.add_argument("--top-k", type=int, default=5, help="检索 Top-K")
    parser.add_argument("--no-recreate", action="store_true", help="不重新创建 collection（复用已有数据）")
    parser.add_argument("--ground-truth", default=GROUND_TRUTH_PATH, help="Ground Truth 文件路径")

    args = parser.parse_args()

    print("=" * 80)
    print("RAG 召回率测试 V2 (使用真实 RAG 组件)")
    print("=" * 80)

    # 1. 加载文档
    print("\n[1/5] 加载 Markdown 文档...")
    docs = load_markdown_files(MARKDOWN_DIR)
    if not docs:
        print("❌ 没有找到文档")
        return

    # 2. 分块
    print("\n[2/5] 文档分块...")
    chunks = chunk_documents(docs)

    # 3. 初始化向量数据库
    print("\n[3/5] 初始化向量数据库...")
    milvus = init_evaluation_collection(chunks, recreate=not args.no_recreate)

    # 4. 初始化全文搜索（可选）
    print("\n[4/5] 初始化全文搜索...")
    meili_index = init_meilisearch_index(chunks, recreate=not args.no_recreate)

    # 5. 加载测试用例
    print("\n[5/5] 加载测试用例...")
    test_cases = load_ground_truth(args.ground_truth)
    if not test_cases:
        print("❌ 没有测试用例")
        return

    # 6. 执行评估
    print("\n" + "=" * 80)
    print("开始评估")
    print("=" * 80)

    vector_result = None
    bm25_result = None
    hybrid_result = None

    if args.mode in ["all", "vector"]:
        vector_result = await evaluate_vector(test_cases, args.top_k)

    if args.mode in ["all", "bm25"]:
        bm25_result = await evaluate_bm25(test_cases, meili_index, args.top_k)

    if args.mode in ["all", "hybrid"]:
        hybrid_result = await evaluate_hybrid(test_cases, args.top_k)

    # 7. 打印结果
    print_results(vector_result, bm25_result, hybrid_result, args.top_k)

    # 8. 保存结果
    output = {
        "meta": {
            "top_k": args.top_k,
            "collection": EVAL_COLLECTION_NAME,
            "total_cases": len(test_cases),
        },
        "vector": vector_result,
        "bm25": bm25_result,
        "hybrid": hybrid_result,
    }

    output_file = "tests/results/recall_test_results_v2.json"
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\n✅ 结果已保存到: {output_file}")


if __name__ == "__main__":
    asyncio.run(main())
