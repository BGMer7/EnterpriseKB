"""
Ground Truth 生成脚本 V2
从 evaluation collection 读取已有 chunks 生成问题
"""
import os
import sys
import json
import random
import re
from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.integrations.milvus_client import MilvusClientWrapper
from app.integrations.llm_server import get_llm_client


# ===== 配置 =====
EVAL_COLLECTION_NAME = "evaluation"  # 从 evaluation collection 读取
OUTPUT_DIR = "tests/results"
RANDOM_SEED = 42


def get_all_chunks_from_milvus() -> List[Dict]:
    """从 Milvus evaluation collection 查询所有 chunks"""
    print(f"\n[查询] 从 {EVAL_COLLECTION_NAME} 获取所有 chunks...")

    milvus = MilvusClientWrapper(collection_name=EVAL_COLLECTION_NAME)
    client = milvus.connect()

    # 检查 collection 是否存在
    if not client.has_collection(EVAL_COLLECTION_NAME):
        print(f"  ❌ Collection {EVAL_COLLECTION_NAME} 不存在")
        print(f"     请先运行 test_recall_v2.py 初始化数据")
        return []

    # 加载 collection
    client.load_collection(EVAL_COLLECTION_NAME)

    # 查询所有数据（通过分页）
    all_chunks = []
    batch_size = 1000
    offset = 0

    while True:
        results = client.query(
            collection_name=EVAL_COLLECTION_NAME,
            filter="",  # 空 filter 表示查询所有
            output_fields=[
                "chunk_id", "document_id", "content", "title",
                "page_number", "section", "chunk_index"
            ],
            limit=batch_size,
            offset=offset
        )

        if not results:
            break

        all_chunks.extend(results)
        offset += len(results)

        if len(results) < batch_size:
            break

    print(f"  ✓ 获取 {len(all_chunks)} 个 chunks")
    return all_chunks


def filter_valid_chunks(chunks: List[Dict]) -> List[Dict]:
    """过滤掉太短或质量差的 chunks"""
    valid = []
    for c in chunks:
        content = c.get("content", "")
        # 过滤条件
        if len(content) < 50:  # 太短
            continue
        if len(content) > 2000:  # 太长，截断
            c["content"] = content[:2000]
        valid.append(c)

    print(f"\n[过滤] 有效 chunks: {len(valid)} / {len(chunks)}")
    return valid


def deduplicate_chunks(chunks: List[Dict], similarity_threshold: float = 0.8) -> List[Dict]:
    """简单去重：基于内容相似度"""
    # 简化：按 document_id 分组，每组最多选 N 个
    by_doc = {}
    for c in chunks:
        doc_id = c.get("document_id", "unknown")
        if doc_id not in by_doc:
            by_doc[doc_id] = []
        by_doc[doc_id].append(c)

    # 每个文档最多选 10 个 chunks，均匀分布
    selected = []
    for doc_id, doc_chunks in by_doc.items():
        if len(doc_chunks) <= 10:
            selected.extend(doc_chunks)
        else:
            # 均匀采样
            step = len(doc_chunks) // 10
            for i in range(0, len(doc_chunks), step):
                if len([s for s in selected if s.get("document_id") == doc_id]) < 10:
                    selected.append(doc_chunks[i])

    print(f"\n[去重] 采样后: {len(selected)} 个 chunks（来自 {len(by_doc)} 个文档）")
    return selected


def generate_questions_from_chunks(
    chunks: List[Dict],
    questions_per_chunk: int = 2,
    use_llm: bool = False
) -> List[Dict]:
    """为每个 chunk 生成问题"""
    print(f"\n[生成] 为 {len(chunks)} 个 chunks 生成问题...")

    random.seed(RANDOM_SEED)

    qa_pairs = []

    for i, chunk in enumerate(chunks, 1):
        content = chunk.get("content", "")
        title = chunk.get("title", "")

        # 基于规则的简单问题生成
        questions = generate_questions_rule_based(content, title, questions_per_chunk)

        for q in questions:
            qa_pairs.append({
                "query_id": f"q{len(qa_pairs)+1:04d}",
                "question": q,
                "relevant_chunk_ids": [chunk["chunk_id"]],
                "relevant_doc_ids": [chunk["document_id"]],
                "ground_truth": content[:500],  # 前 500 字符作为答案
                "metadata": {
                    "source_chunk_id": chunk["chunk_id"],
                    "source_title": title,
                    "page_number": chunk.get("page_number"),
                    "generation_method": "rule_based"
                }
            })

        if i % 10 == 0 or i == len(chunks):
            print(f"  进度: {i}/{len(chunks)} -> {len(qa_pairs)} 个问题")

    print(f"\n✓ 共生成 {len(qa_pairs)} 个问题")
    return qa_pairs


def generate_questions_rule_based(content: str, title: str, n: int) -> List[str]:
    """基于规则从内容生成问题"""
    questions = []

    # 提取关键句子（包含数字、百分比、年份等的句子）
    sentences = re.split(r'[。！?!；;]', content)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 10]

    # 1. 数字类问题
    number_pattern = re.compile(r'(\d+(?:\.\d+)?)\s*(%|亿|万|元|美元|吨|人|家)')
    for sent in sentences:
        match = number_pattern.search(sent)
        if match and len(questions) < n:
            value, unit = match.groups()
            # 生成问题
            if unit == '%':
                q = f"{title}的某个比例是多少？"
            elif unit in ['亿', '万']:
                q = f"{title}相关数据规模是多少？"
            elif '元' in unit:
                q = f"{title}涉及的金额是多少？"
            else:
                q = f"{title}相关的数量指标是多少？"

            if q not in questions:
                questions.append(q)

    # 2. 时间类问题
    time_pattern = re.compile(r'(20\d{2}[-/年]\d{1,2}|[一二三四五六七八九十]+月|Q[1-4]|第[一二三四]季度)')
    for sent in sentences:
        match = time_pattern.search(sent)
        if match and len(questions) < n:
            q = f"{title}在{match.group(1)}的情况如何？"
            if q not in questions:
                questions.append(q)

    # 3. 如果没有提取到足够问题，生成通用问题
    while len(questions) < n:
        templates = [
            f"关于{title}，有哪些关键信息？",
            f"{title}的主要内容是什么？",
            f"{title}涉及哪些方面？",
            f"请介绍{title}的相关情况。",
        ]
        for t in templates:
            if t not in questions and len(questions) < n:
                questions.append(t)

    return questions[:n]


def split_chunk_and_answer_level(qa_pairs: List[Dict]) -> Dict:
    """拆分为 chunk-level 和 answer-level"""
    # Chunk-level: 用于 Recall@K 评测
    chunk_level = []

    # Answer-level: 用于 RAGAS 等端到端评测
    answer_level = []

    for qa in qa_pairs:
        # Chunk-level
        chunk_level.append({
            "query_id": qa["query_id"],
            "question": qa["question"],
            "relevant_chunk_ids": qa["relevant_chunk_ids"],
            "relevant_doc_ids": qa["relevant_doc_ids"],
            "ground_truth": qa["ground_truth"],
            "metadata": qa["metadata"]
        })

        # Answer-level（合并相同问题的答案）
        # 这里简化处理，每个问题对应一个答案
        answer_level.append({
            "query_id": qa["query_id"],
            "question": qa["question"],
            "ground_truth_answer": qa["ground_truth"],
            "source_doc_ids": qa["relevant_doc_ids"],
            "metadata": qa["metadata"]
        })

    return {
        "chunk_level": chunk_level,
        "answer_level": answer_level
    }


def save_ground_truth(data: Dict, output_path: str):
    """保存 ground truth 数据集"""
    print(f"\n[保存] Ground Truth 数据集...")

    # 添加元信息
    output = {
        "meta": {
            "created_at": datetime.now().isoformat(),
            "collection": EVAL_COLLECTION_NAME,
            "random_seed": RANDOM_SEED,
            "total_questions": len(data.get("chunk_level", [])),
        },
        **data
    }

    # 保存
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"  ✓ 保存到: {output_path}")
    print(f"    - chunk_level: {len(data['chunk_level'])} 条")
    print(f"    - answer_level: {len(data['answer_level'])} 条")


def main():
    """主流程"""
    import argparse

    parser = argparse.ArgumentParser(description="生成 Ground Truth 数据集 V2")
    parser.add_argument("--questions-per-chunk", type=int, default=2,
                        help="每个 chunk 生成几个问题")
    parser.add_argument("--max-chunks", type=int, default=100,
                        help="最多处理多少个 chunks")
    parser.add_argument("--output", default="tests/results/ground_truth_v2.json",
                        help="输出文件路径")

    args = parser.parse_args()

    print("=" * 80)
    print("Ground Truth 生成脚本 V2")
    print("=" * 80)
    print(f"从 {EVAL_COLLECTION_NAME} collection 读取 chunks")
    print("=" * 80)

    # 1. 从 Milvus 获取所有 chunks
    chunks = get_all_chunks_from_milvus()
    if not chunks:
        return

    # 2. 过滤有效 chunks
    chunks = filter_valid_chunks(chunks)

    # 3. 去重采样
    chunks = deduplicate_chunks(chunks)

    # 4. 限制数量
    if len(chunks) > args.max_chunks:
        random.seed(RANDOM_SEED)
        chunks = random.sample(chunks, args.max_chunks)
        print(f"\n[采样] 随机选取 {len(chunks)} 个 chunks")

    # 5. 生成问题
    qa_pairs = generate_questions_from_chunks(
        chunks,
        questions_per_chunk=args.questions_per_chunk
    )

    # 6. 拆分 level
    data = split_chunk_and_answer_level(qa_pairs)

    # 7. 保存
    save_ground_truth(data, args.output)

    print("\n" + "=" * 80)
    print("✅ 完成！")
    print("=" * 80)
    print(f"\n生成的 Ground Truth 与 evaluation collection 完全一致")
    print(f"可以直接用于 test_recall_v2.py 进行评估")


if __name__ == "__main__":
    main()
