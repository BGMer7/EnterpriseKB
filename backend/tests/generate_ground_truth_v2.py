"""
Ground Truth 生成脚本 V2 (LLM版)
从 evaluation collection 读取已有 chunks，使用 LLM 生成问题
"""
import os
import sys
import json
import random
import asyncio
import re
import aiohttp
from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.integrations.milvus_client import MilvusClientWrapper
from app.config import settings


# ===== 配置 =====
EVAL_COLLECTION_NAME = "evaluation"  # 从 evaluation collection 读取
OUTPUT_DIR = "tests/results"
RANDOM_SEED = 42

# LLM 配置
LLM_API_URL = settings.LLM_API_URL
LLM_API_KEY = settings.LLM_API_KEY or "dummy"
LLM_MODEL = settings.LLM_MODEL_NAME
LLM_MAX_TOKENS = 2000
LLM_TEMPERATURE = 0.7
MAX_CONCURRENCY = 10  # 并发数


# ===== Prompt 模板 =====
QUESTION_GENERATION_SYSTEM_PROMPT = """你是一个专业的金融/产业研究报告分析师，专门负责生成RAG评估问题。

你的任务是：
1. 阅读提供的文档内容
2. 生成1个高质量的评估问题
3. 问题要能测试R系统的信息检索和理解能力

生成的问题要求：
- 基于文档中的具体数据、信息和观点
- 不要包含任何文件名字、ID或标识符（如 H3_xxx）
- 问题要自然、像真实用户提问
- 问题类型可以是：数字类、时间类、对比类、趋势类等

输出格式：JSON数组，只包含1个问题字符串
例如：["2026年3月焦煤价格相比2月上涨了多少？"]"""

QUESTION_GENERATION_USER_PROMPT = """请根据以下文档内容生成1个评估问题。

要求：
1. 问题基于文档中的具体信息
2. 不要使用文件名、ID等标识符
3. 问题要自然流畅

---
{content}
---

请生成1个问题，输出JSON数组："""


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
        if len(content) > 3000:  # 太长，截断
            c["content"] = content[:3000]
        valid.append(c)

    print(f"\n[过滤] 有效 chunks: {len(valid)} / {len(chunks)}")
    return valid


def deduplicate_chunks(chunks: List[Dict]) -> List[Dict]:
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


async def call_llm_async(
    session: aiohttp.ClientSession,
    content: str,
    retry_count: int = 3
) -> List[str]:
    """异步调用 LLM 生成问题"""
    user_prompt = QUESTION_GENERATION_USER_PROMPT.format(content=content)

    payload = {
        "model": LLM_MODEL,
        "messages": [
            {"role": "system", "content": QUESTION_GENERATION_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ],
        "max_tokens": LLM_MAX_TOKENS,
        "temperature": LLM_TEMPERATURE,
        "response_format": {"type": "json_object"}
    }

    headers = {
        "Authorization": f"Bearer {LLM_API_KEY}",
        "Content-Type": "application/json"
    }

    for attempt in range(retry_count):
        try:
            async with session.post(
                f"{LLM_API_URL}/chat/completions",
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=120)
            ) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    text = result["choices"][0]["message"]["content"]

                    # 解析 JSON 数组
                    try:
                        questions = json.loads(text)
                        if isinstance(questions, list):
                            return [q for q in questions if isinstance(q, str) and len(q) > 0]
                    except json.JSONDecodeError:
                        # 尝试从文本中提取 JSON
                        match = re.search(r'\[.*\]', text, re.DOTALL)
                        if match:
                            questions = json.loads(match.group())
                            if isinstance(questions, list):
                                return [q for q in questions if isinstance(q, str) and len(q) > 0]

                    print(f"    ⚠️ 解析失败，使用默认问题")
                    return ["请介绍文档中的关键信息。"]

                elif resp.status == 429:
                    # Rate limit，等待后重试
                    await asyncio.sleep(5 * (attempt + 1))
                    continue
                else:
                    print(f"    ⚠️ API错误 {resp.status}")
                    break

        except asyncio.TimeoutError:
            print(f"    ⚠️ 超时 (尝试 {attempt + 1}/{retry_count})")
            await asyncio.sleep(2)
        except Exception as e:
            print(f"    ⚠️ 异常: {str(e)[:50]}")
            break

    # 失败时返回默认问题
    return ["请介绍文档中的主要内容和数据。"]


async def generate_questions_llm(
    chunks: List[Dict],
    questions_per_chunk: int = 2
) -> List[Dict]:
    """使用 LLM 为每个 chunk 生成问题"""
    print(f"\n[LLM生成] 为 {len(chunks)} 个 chunks 生成问题...")
    print(f"  并发数: {MAX_CONCURRENCY}")

    qa_pairs = []
    semaphore = asyncio.Semaphore(MAX_CONCURRENCY)

    async def process_chunk(chunk: Dict, index: int):
        async with semaphore:
            content = chunk.get("content", "")[:2000]  # 限制输入长度

            async with aiohttp.ClientSession() as session:
                questions = await call_llm_async(session, content)

            # 限制问题数量
            questions = questions[:questions_per_chunk]

            # 如果不够，用默认值填充
            while len(questions) < questions_per_chunk:
                questions.append("请介绍文档中的关键信息。")

            for q in questions:
                qa_pairs.append({
                    "query_id": f"q{len(qa_pairs)+1:04d}",
                    "question": q,
                    "relevant_chunk_ids": [chunk["chunk_id"]],
                    "relevant_doc_ids": [chunk["document_id"]],
                    "ground_truth": chunk.get("content", "")[:500],
                    "metadata": {
                        "source_chunk_id": chunk["chunk_id"],
                        "source_title": chunk.get("title", ""),
                        "page_number": chunk.get("page_number"),
                        "generation_method": "llm"
                    }
                })

            if (index + 1) % 10 == 0 or (index + 1) == len(chunks):
                print(f"  进度: {index + 1}/{len(chunks)} -> {len(qa_pairs)} 个问题")

    # 并发执行
    tasks = [process_chunk(chunk, i) for i, chunk in enumerate(chunks)]
    await asyncio.gather(*tasks)

    print(f"\n✓ 共生成 {len(qa_pairs)} 个问题")
    return qa_pairs


def generate_questions_from_chunks(
    chunks: List[Dict],
    questions_per_chunk: int = 2,
    use_llm: bool = True
) -> List[Dict]:
    """为每个 chunk 生成问题（统一入口）"""
    return asyncio.run(generate_questions_llm(chunks, questions_per_chunk))


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

        # Answer-level
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
            "generation_method": "llm"
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

    parser = argparse.ArgumentParser(description="生成 Ground Truth 数据集 V2 (LLM版)")
    parser.add_argument("--questions", type=int, default=10,
                        help="总共生成几个问题（默认10个）")
    parser.add_argument("--output", default="tests/results/ground_truth_v2.json",
                        help="输出文件路径")
    parser.add_argument("--concurrency", type=int, default=5,
                        help="LLM 并发数")
    parser.add_argument("--markdown-dir", default="src/static/miner_output",
                        help="Markdown 文件目录")

    args = parser.parse_args()

    global MAX_CONCURRENCY
    MAX_CONCURRENCY = args.concurrency

    print("=" * 80)
    print("Ground Truth 生成脚本 V2 (LLM版)")
    print("=" * 80)
    print(f"从 {args.markdown_dir} 读取 Markdown 文件")
    print(f"使用 LLM: {LLM_MODEL}")
    print(f"目标问题数: {args.questions}")
    print("=" * 80)

    # 1. 从本地 Markdown 文件读取并分块
    print("\n[1/4] 加载 Markdown 文件...")
    from pathlib import Path
    docs = {}
    dir_path = Path(args.markdown_dir)
    if not dir_path.exists():
        print(f"  ❌ 目录不存在: {args.markdown_dir}")
        return

    for md_file in dir_path.glob("*.md"):
        try:
            with open(md_file, "r", encoding="utf-8") as f:
                content = f.read()
                doc_name = md_file.stem.replace("MinerU_markdown_", "")
                docs[doc_name] = {"title": doc_name, "content": content}
                print(f"  ✓ 加载: {md_file.name} ({len(content)} 字符)")
        except Exception as e:
            print(f"  ✗ 加载失败 {md_file.name}: {e}")

    print(f"\n📚 总计加载: {len(docs)} 个文档")

    # 2. 使用 Markdown 分块
    print("\n[2/4] 使用 Markdown 结构化分块...")
    from app.processors.chunker import chunk_by_strategy

    doc_chunks = {}  # 按文档存储 chunks
    all_chunks = []

    for doc_id, doc_info in docs.items():
        chunks = chunk_by_strategy(
            document_id=doc_id,
            content=doc_info["content"],
            pages=[{"page_number": 1, "content": doc_info["content"]}],
            strategy="markdown",
            chunk_size=512,
            chunk_overlap=64
        )

        # 过滤太短的 chunk
        valid_chunks = [c for c in chunks if len(c.get("content", "")) >= 100]
        doc_chunks[doc_id] = valid_chunks

        for chunk in valid_chunks:
            chunk["title"] = doc_info["title"]
            all_chunks.append(chunk)

        print(f"  - {doc_id}: {len(valid_chunks)}/{len(chunks)} chunks")

    print(f"\n📦 总计 chunks: {len(all_chunks)}")

    # 3. 分文档采样 - 每个文档随机选 1-2 个有代表性的 chunk
    print("\n[3/4] 分文档采样...")

    # 按内容长度排序，每个文档选择内容较丰富的 chunk
    sampled_chunks = []
    chunks_per_doc = max(1, args.questions // len(docs))  # 每个文档分配几个

    for doc_id, chunks in doc_chunks.items():
        if not chunks:
            continue

        # 按内容长度降序，选择内容较丰富的
        sorted_chunks = sorted(chunks, key=lambda x: len(x.get("content", "")), reverse=True)

        # 选择前 N 个（内容最丰富的）
        selected = sorted_chunks[:chunks_per_doc]
        sampled_chunks.extend(selected)
        print(f"  - {doc_id}: 选取 {len(selected)} 个")

    # 如果还不够，随机补充
    remaining = args.questions - len(sampled_chunks)
    if remaining > 0:
        unsampled = [c for c in all_chunks if c not in sampled_chunks]
        if unsampled:
            random.seed(RANDOM_SEED)
            additional = random.sample(unsampled, min(remaining, len(unsampled)))
            sampled_chunks.extend(additional)
            print(f"  - 补充: {len(additional)} 个")

    print(f"\n[采样] 共选取 {len(sampled_chunks)} 个 chunks 用于生成问题")

    # 4. 使用 LLM 生成问题
    qa_pairs = generate_questions_from_chunks(
        sampled_chunks,
        questions_per_chunk=1
    )

    # 5. 拆分 level
    data = split_chunk_and_answer_level(qa_pairs)

    # 6. 保存
    save_ground_truth(data, args.output)

    print("\n" + "=" * 80)
    print("✅ 完成！")
    print("=" * 80)
    print(f"\n使用 LLM 生成的问题已保存到 {args.output}")
    print(f"可以直接用于 test_recall_v2.py 进行评估")


if __name__ == "__main__":
    main()