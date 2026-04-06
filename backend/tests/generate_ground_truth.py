"""
自动生成 Ground Truth 数据集
使用 LLM 为每个 chunk 生成问题+答案，建立：
  - chunk_level:  query → chunk_id  （用于 Recall@K / MRR / Hit Rate）
  - answer_level: query → ground_truth（用于 RAGAS ContextRecall）
"""
import os
import sys
import io
import json
import asyncio
import random
import re
import uuid
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict
from pathlib import Path

# 设置 stdout 编码
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace", line_buffering=True)

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 强制使用 CPU
os.environ["CUDA_VISIBLE_DEVICES"] = ""
os.environ.setdefault("LOG_LEVEL", "WARNING")


# ===== 配置 =====

MARKDOWN_DIR = "src/static/miner_output"
OUTPUT_FILE = "tests/ground_truth/ground_truth_auto_dataset.json"

# 每个 chunk 最多生成几个问题（建议 1-2，太多会引入噪声）
QUESTIONS_PER_CHUNK = 1

# 随机抽取多少个 chunk（None = 全量）
SAMPLE_SIZE: Optional[int] = 20


# chunk 送给 LLM 时的最大字符数
CHUNK_PREVIEW_LEN = 1500

# 分块参数，必须与生产环境一致！
# 使用真实的 DocumentChunker
CHUNK_SIZE = 512  # tokens，与 DocumentChunker 默认一致
CHUNK_OVERLAP = 50
MIN_CHUNK_SIZE = 100
CHUNK_STRATEGY = "semantic"  # fixed, semantic, structural

RANDOM_SEED = 42

# 导入真实的 DocumentChunker
from app.processors.chunker import DocumentChunker, Chunk


# ===== 数据结构 =====

@dataclass
class ChunkData:
    chunk_id: str
    document_id: str
    content: str
    title: str
    chunk_index: int
    page_number: Optional[int] = None
    section: Optional[str] = None


@dataclass
class ChunkLevelCase:
    """用于 Recall@K / MRR / Hit Rate 评测"""
    query_id: str
    question: str
    relevant_chunk_ids: List[str]   # 关键：chunk-ID 级别的 ground truth
    ground_truth: str               # 同时保留答案文本，方便 RAGAS 复用
    document_id: str
    title: str
    content_preview: str            # chunk 内容摘要，方便人工抽检
    source: str = "chunk_content"


@dataclass
class AnswerLevelCase:
    """用于 RAGAS ContextRecall / ContextPrecision 评测"""
    query_id: str
    question: str
    ground_truth: str
    document_id: str
    title: str
    source: str = "document_title"
    # 评测时动态填入，构建时留空
    contexts: List[str] = field(default_factory=list)


# ===== 分块器 =====
# ⚠️ 重要：生产环境请替换为实际使用的 chunker，保证 chunk_id 对得上
# from app.rag.chunker import ProductionChunker



# ===== 文档加载 =====

def load_markdown_files(directory: str) -> Dict[str, Tuple[str, str]]:
    """
    返回 {doc_id: (title, content)}
    """
    docs: Dict[str, Tuple[str, str]] = {}
    dir_path = Path(directory)

    if not dir_path.exists():
        print(f"❌ 目录不存在: {directory}")
        return docs

    for md_file in dir_path.glob("*.md"):
        try:
            content = md_file.read_text(encoding="utf-8")
            doc_id = md_file.stem.replace("MinerU_markdown_", "")

            # 提取首个一级标题作为 title
            title = doc_id
            for line in content.split("\n")[:10]:
                line = line.strip()
                if line.startswith("# "):
                    title = line[2:].strip()
                    break

            docs[doc_id] = (title, content)
            print(f"  ✓ 加载: {md_file.name} ({len(content):,} 字符)")
        except Exception as e:
            print(f"  ✗ 加载失败 {md_file.name}: {e}")

    print(f"\n📚 总计加载: {len(docs)} 个文档")
    return docs


# ===== LLM 调用 =====
async def call_llm_json(llm_client, messages: List[Dict], max_tokens: int = 600) -> Optional[Dict]:
    try:
        response: str = await llm_client.generate(
            messages=messages,
            max_tokens=max_tokens,
            temperature=0.3,
        )
        text = response.strip()
        
        # 去除 <think>...</think> 块（DeepSeek-R1 等推理模型会输出）
        text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()
        
        # 去除 markdown 代码块包裹
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
        
        return json.loads(text)
    except json.JSONDecodeError as e:
        print(f"  ⚠️ JSON 解析失败: {e} | 原始响应: {response[:200]}")
        return None
    except Exception as e:
        print(f"  ⚠️ LLM 调用失败: {e}")
        return None
    question = result.get("question", "").strip()



# ===== 核心生成逻辑 =====

async def generate_from_chunk(chunk: ChunkData, llm_client) -> Optional[ChunkLevelCase]:
    """
    基于单个 chunk 生成一条 chunk_level ground truth。
    同时包含 question + ground_truth answer，一次 LLM 调用搞定。
    """
    content_preview = chunk.content[:CHUNK_PREVIEW_LEN]

    prompt = f"""根据以下文档片段，生成1个具体问题及其标准答案。

要求：
1. 问题必须能从该片段中直接找到答案，以"？"结尾
2. 问题要包含具体数据或事实，像真实用户提问
3. 答案简洁准确，直接基于文档内容，不要编造
4. 严格返回以下 JSON 格式，不要有其他内容：
{{
  "question": "问题内容？",
  "answer": "标准答案文本"
}}

文档片段：
{content_preview}"""

    result = await call_llm_json(llm_client, [{"role": "user", "content": prompt}])

    if not result:
        return None

    question = result.get("question", "").strip()
    answer = result.get("answer", "").strip()

    # 基本质量过滤
    if not question or not answer:
        return None
    if len(question) < 8 or not question.endswith("？"):
        return None
    if len(answer) < 5:
        return None

    return ChunkLevelCase(
        query_id=f"chunk_{uuid.uuid4().hex[:8]}",
        question=question,
        relevant_chunk_ids=[chunk.chunk_id],
        ground_truth=answer,
        document_id=chunk.document_id,
        title=chunk.title,
        content_preview=chunk.content[:300],
    )


async def generate_from_title(doc_id: str, title: str, content: str, llm_client) -> Optional[AnswerLevelCase]:
    """
    基于文档标题生成一条 answer_level ground truth。
    此类问题跨越多个 chunk，无法对应具体 chunk_id，
    只能用于 RAGAS ContextRecall，不用于 Recall@K。
    """
    # 取文档前 2000 字作为上下文，帮助 LLM 理解文档范围
    doc_preview = content[:2000]

    prompt = f"""根据以下研报的标题和摘要内容，生成1个关于该研报核心结论的问题及标准答案。

要求：
1. 问题要关注研报的核心结论或关键数据，以"？"结尾
2. 答案要基于文档内容，简洁准确
3. 严格返回以下 JSON 格式，不要有其他内容：
{{
  "question": "问题内容？",
  "answer": "标准答案文本"
}}

研报标题：{title}

文档摘要：
{doc_preview}"""

    result = await call_llm_json(llm_client, [{"role": "user", "content": prompt}], max_tokens=400)

    if not result:
        return None

    question = result.get("question", "").strip()
    answer = result.get("answer", "").strip()

    if not question or not answer or len(question) < 8:
        return None

    return AnswerLevelCase(
        query_id=f"title_{uuid.uuid4().hex[:8]}",
        question=question,
        ground_truth=answer,
        document_id=doc_id,
        title=title,
    )


# ===== 主流程 =====

async def generate_ground_truth():
    print("\n" + "=" * 60)
    print("自动生成 Ground Truth 数据集")
    print("=" * 60)

    # 1. 加载文档
    print("\n[1/5] 加载 Markdown 文档...")
    docs = load_markdown_files(MARKDOWN_DIR)
    if not docs:
        print("❌ 没有找到文档，退出")
        return

    # 2. 分块
    # ⚠️ 必须与生产环境的切块逻辑一致，否则 chunk_id 无法对应
    print("\n[2/5] 文档分块...")
    # 使用真实的 DocumentChunker
    chunker = DocumentChunker(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        min_chunk_size=MIN_CHUNK_SIZE
    )
    all_chunks: List[ChunkData] = []

    for doc_id, (title, content) in docs.items():
        # DocumentChunker 需要 pages 参数，我们构造一个简化的
        pages = [{"page_number": 1, "content": content}]
        chunks = chunker.chunk(doc_id, content, pages, strategy=CHUNK_STRATEGY)
        # 转换为 ChunkData 格式
        for chunk in chunks:
            all_chunks.append(ChunkData(
                chunk_id=chunk.id,
                document_id=chunk.document_id,
                content=chunk.content,
                title=title,
                chunk_index=chunk.chunk_index,
            ))
        print(f"  - {doc_id[:40]}: {len(chunks)} 个 chunks")

    print(f"\n📦 总计 chunks: {len(all_chunks)}")

    # 3. 连接 LLM
    print("\n[3/5] 连接 LLM...")
    from app.integrations.llm_server import get_llm_client
    from app.config import settings

    llm_client = get_llm_client()
    print(f"  - Model: {settings.LLM_MODEL_NAME}")
    print(f"  - API:   {settings.LLM_API_URL}")

    # 4. chunk_level：为每个 chunk 生成问题+答案
    print("\n[4/5] 生成 chunk_level ground truth...")

    random.seed(RANDOM_SEED)
    selected_chunks = (
        random.sample(all_chunks, min(SAMPLE_SIZE, len(all_chunks)))
        if SAMPLE_SIZE
        else all_chunks
    )
    print(f"  - 选取 {len(selected_chunks)} / {len(all_chunks)} 个 chunks")

    chunk_level_cases: List[ChunkLevelCase] = []
    failed_count = 0

    for i, chunk in enumerate(selected_chunks, 1):
        case = await generate_from_chunk(chunk, llm_client)
        if case:
            chunk_level_cases.append(case)
        else:
            failed_count += 1

        if i % 10 == 0 or i == len(selected_chunks):
            print(f"  - 进度: {i}/{len(selected_chunks)} | 成功: {len(chunk_level_cases)} | 失败: {failed_count}")

    print(f"  ✓ chunk_level 生成完成: {len(chunk_level_cases)} 条")

    # 5. answer_level：基于文档标题生成跨 chunk 问题
    print("\n[5/5] 生成 answer_level ground truth（基于文档标题）...")

    answer_level_cases: List[AnswerLevelCase] = []

    for doc_id, (title, content) in docs.items():
        case = await generate_from_title(doc_id, title, content, llm_client)
        if case:
            answer_level_cases.append(case)
            print(f"  ✓ {title[:40]}")
        else:
            print(f"  ✗ 生成失败: {title[:40]}")

    print(f"  ✓ answer_level 生成完成: {len(answer_level_cases)} 条")

    # 6. 保存结果
    output_data = {
        "meta": {
            "description": "自动生成的 Ground Truth 数据集",
            "source_dir": MARKDOWN_DIR,
            "chunk_size": CHUNK_SIZE,
            "chunk_overlap": CHUNK_OVERLAP,
            "min_chunk_size": MIN_CHUNK_SIZE,
            "chunk_strategy": CHUNK_STRATEGY,
            "total_documents": len(docs),
            "total_chunks": len(all_chunks),
            "selected_chunks": len(selected_chunks),
            "random_seed": RANDOM_SEED,
        },
        "stats": {
            "chunk_level_count": len(chunk_level_cases),
            "answer_level_count": len(answer_level_cases),
            "total": len(chunk_level_cases) + len(answer_level_cases),
        },
        # chunk_level: 用于 Recall@K / MRR / Hit Rate
        # relevant_chunk_ids 是评测检索效果的 ground truth
        "chunk_level": [asdict(c) for c in chunk_level_cases],

        # answer_level: 用于 RAGAS ContextRecall / ContextPrecision
        # 评测时将检索结果填入 contexts 字段
        "answer_level": [asdict(c) for c in answer_level_cases],
    }

    output_path = Path(OUTPUT_FILE)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output_data, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\n✅ 已保存到: {OUTPUT_FILE}")
    print(f"   - chunk_level:  {len(chunk_level_cases)} 条（Recall@K 评测用）")
    print(f"   - answer_level: {len(answer_level_cases)} 条（RAGAS 评测用）")

    # 打印示例
    print("\n📋 chunk_level 示例：")
    for c in chunk_level_cases[:3]:
        print(f"  Q: {c.question}")
        print(f"  A: {c.ground_truth[:60]}...")
        print(f"  → chunk_id: {c.relevant_chunk_ids}")
        print()

    print("📋 answer_level 示例：")
    for c in answer_level_cases[:2]:
        print(f"  Q: {c.question}")
        print(f"  A: {c.ground_truth[:60]}...")
        print()

    return output_data


# ===== 评测工具（独立函数，可单独调用）=====

def evaluate_retrieval(retriever, ground_truth_path: str, top_k: int = 5) -> Dict[str, float]:
    """
    使用 chunk_level 数据评测检索效果。

    Args:
        retriever: 你的检索器，需实现 retrieve(query, top_k) -> List[有 .id 属性的对象]
        ground_truth_path: ground truth JSON 文件路径
        top_k: 检索 Top-K

    Returns:
        包含 hit_rate、recall、mrr、precision 的指标字典
    """
    data = json.loads(Path(ground_truth_path).read_text(encoding="utf-8"))
    cases = data["chunk_level"]

    if not cases:
        print("⚠️ chunk_level 数据为空，无法评测")
        return {}

    metrics: Dict[str, List[float]] = {
        f"hit_rate@{top_k}": [],
        f"recall@{top_k}": [],
        "mrr": [],
        f"precision@{top_k}": [],
    }

    for case in cases:
        query = case["question"]
        relevant_ids = set(case["relevant_chunk_ids"])

        retrieved = retriever.retrieve(query, top_k=top_k)
        retrieved_ids = [doc.id for doc in retrieved]

        # Hit Rate@K：Top-K 中至少命中 1 个
        hit = int(any(rid in relevant_ids for rid in retrieved_ids))
        metrics[f"hit_rate@{top_k}"].append(hit)

        # Recall@K：ground truth 中有多少被召回
        recalled = len(set(retrieved_ids) & relevant_ids)
        metrics[f"recall@{top_k}"].append(recalled / len(relevant_ids))

        # Precision@K：Top-K 中有多少是相关的
        metrics[f"precision@{top_k}"].append(recalled / top_k)

        # MRR：第一个相关文档的排名倒数
        mrr = 0.0
        for rank, rid in enumerate(retrieved_ids, 1):
            if rid in relevant_ids:
                mrr = 1.0 / rank
                break
        metrics["mrr"].append(mrr)

    result = {k: round(sum(v) / len(v), 4) for k, v in metrics.items()}
    print("\n📊 检索评测结果：")
    for k, v in result.items():
        print(f"  {k}: {v:.4f}")
    return result


if __name__ == "__main__":
    asyncio.run(generate_ground_truth())