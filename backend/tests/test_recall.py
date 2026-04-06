"""
召回率测试脚本
基于 MinerU 解析的 Markdown 文档测试 RAG 系统的召回率
使用简单的 TF-IDF 实现，不依赖 torch
"""
import os
import sys
import io
import json
import re
import math
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

# 导入真实的 DocumentChunker
from app.processors.chunker import DocumentChunker, Chunk
from pathlib import Path

# 设置stdout编码为utf-8，避免emoji打印问题
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True)

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 强制使用CPU运行
os.environ["CUDA_VISIBLE_DEVICES"] = ""
os.environ.setdefault("LOG_LEVEL", "WARNING")


# ===== 数据结构 =====

@dataclass
class TestCase:
    """测试用例"""
    question: str  # 查询问题
    relevant_docs: List[str]  # 相关的文档ID列表（用于计算召回率）
    ground_truth: str = ""  # 标准答案（用于RAGAS评估）


@dataclass
class ChunkData:
    """文档块数据"""
    chunk_id: str
    document_id: str
    content: str
    title: str
    chunk_index: int
    page_number: Optional[int]
    section: Optional[str]


# ===== 配置 =====

# Markdown 文档目录（相对于项目根目录）
MARKDOWN_DIR = "src/static/miner_output"

# 测试用例 - 基于 MinerU 解析的真实金融研报内容
# 文档ID提取: MinerU_markdown_{doc_id}.md
# 数据来源: backend/src/static/miner_output/
#
# 文档列表:
# 1. 东方财富(300059) - 2025年三季报点评
# 2. 保险行业月报 - 寿险开门红、车险承压
# 3. 小马智行(PONY) - Robotaxi业务爆发
# 4. 银行理财周报 - 适当性管理规范
# 5. Symbotic(SYM.O) - 仓储自动化
# 6. 算电协同 - 国家战略
# 7. 英伟达(NVDA) - Blackwell平台
# 8. 赛英电子 - 新股覆盖
# 9. 煤炭 - 中东局势与焦煤
#
# 每个测试用例包含:
#   question: 基于文档内容设计的具体问题
#   relevant_docs: 应该被检索到的文档ID
#   ground_truth: 标准答案（用于RAGAS评估）

TEST_CASES = [
    # 文档1: 东方财富 - 2025年三季报
    TestCase(
        question="2025年三季度东方财富的经纪业务和两融业务表现如何？",
        relevant_docs=["H3_AP202510251768729037_1_2041087592891666432"],
        ground_truth="经纪及两融稳健增长，固收波动影响自营收益下滑"
    ),
    # 文档2: 保险行业月报
    TestCase(
        question="2026年1-2月人身险公司原保费收入同比增长多少？",
        relevant_docs=["H3_AP202603281820832133_1_2041085714053189632"],
        ground_truth="人身险公司原保费收入同比+9.7%，其中1月同比+13.0%，2月同比+1.2%"
    ),
    TestCase(
        question="2026年1-2月车险保费累计同比变化是多少？",
        relevant_docs=["H3_AP202603281820832133_1_2041085714053189632"],
        ground_truth="车险累计保费同比-0.9%，连续两个月同比下滑"
    ),
    # 文档3: 小马智行
    TestCase(
        question="小马智行的Robotaxi业务目前处于什么发展阶段？",
        relevant_docs=["H3_AP202603301820856165_1_2041087231611101184"],
        ground_truth="Robotaxi业务爆发式放量，全球化商业进程显著提速"
    ),
    # 文档4: 银行理财
    TestCase(
        question="理财公司产品适当性管理自律规范什么时候正式施行？",
        relevant_docs=["H3_AP202604011820960351_1_2041087491825725440"],
        ground_truth="2026年7月1日正式施行"
    ),
    TestCase(
        question="上周现金管理类产品近7日年化收益率是多少？",
        relevant_docs=["H3_AP202604011820960351_1_2041087491825725440"],
        ground_truth="近7日年化收益率录得1.24%，环比上升3BP"
    ),
    # 文档5: Symbotic
    TestCase(
        question="Symbotic的仓储自动化平台主要服务哪些类型的客户？",
        relevant_docs=["H3_AP202604021820975530_1_2041087518715400192"],
        ground_truth="主要服务零售、批发商等大型客户，提供仓储自动化解决方案"
    ),
    # 文档6: 算电协同
    TestCase(
        question="算电协同纳入国家战略后，对数据中心用电量有什么影响？",
        relevant_docs=["H3_AP202604031821007973_1_2041087628560035840"],
        ground_truth="2025年我国数据中心用电量1933亿度，占全社会用电量1.9%，同比增速17.0%；2026年1-2月同比大增46.2%"
    ),
    TestCase(
        question="数据中心对绿电占比有什么要求？",
        relevant_docs=["H3_AP202604031821007973_1_2041087628560035840"],
        ground_truth="国家枢纽节点新建数据中心绿电占比要求超过80%"
    ),
    # 文档7: 英伟达
    TestCase(
        question="英伟达FY2026第四季度营收是多少？数据中心收入占比多少？",
        relevant_docs=["H3_AP202604031821009525_1_2041087542560018432"],
        ground_truth="FY2026 Q4营收681.3亿美元，同比增长73%；数据中心收入623.14亿美元，占总营收91%"
    ),
    TestCase(
        question="Blackwell平台在数据中心营收中的占比是多少？",
        relevant_docs=["H3_AP202604031821009525_1_2041087542560018432"],
        ground_truth="Grace Blackwell系统在第四财季数据中心营收中占比达到三分之二"
    ),
    # 文档8: 赛英电子
    TestCase(
        question="赛英电子的主要业务是什么？",
        relevant_docs=["H3_AP202604051821026931_1_2041087701608034304"],
        ground_truth="新股覆盖，具体业务需要阅读研报全文"
    ),
    # 文档9: 煤炭
    TestCase(
        question="截至4月3日，秦港Q5500动力煤平仓价是多少？",
        relevant_docs=["H3_AP202604061821030492_1_2041087660432551936"],
        ground_truth="秦港Q5500动力煤平仓价为754元/吨，环比下跌7元/吨"
    ),
    TestCase(
        question="京唐港主焦煤报价是多少？与底部相比反弹了多少？",
        relevant_docs=["H3_AP202604061821030492_1_2041087660432551936"],
        ground_truth="京唐港主焦煤报价1620元/吨，从2025年七月初1230元的底部反弹"
    ),
    TestCase(
        question="动力煤价格的目标区间是多少？",
        relevant_docs=["H3_AP202604061821030492_1_2041087660432551936"],
        ground_truth="目标区间为800-860元，煤电盈利均分线为750元"
    ),
]


# ===== 简单的中文分词 =====

def simple_tokenizer(text: str) -> List[str]:
    """简单的中文分词"""
    # 提取2-4个连续汉字作为词
    chinese_words = re.findall(r'[\u4e00-\u9fff]{2,4}', text)
    # 提取英文和数字作为词
    english_words = re.findall(r'[a-zA-Z0-9]{2,}', text)
    return chinese_words + english_words


# ===== 简单的 TF-IDF 向量器 =====

class SimpleTFIDFVectorizer:
    """简单的 TF-IDF 向量化器"""

    def __init__(self):
        self.vocabulary: Dict[str, int] = {}
        self.idf: Dict[str, float] = {}
        self.doc_count = 0
        self.fitted = False

    def fit(self, documents: List[str]):
        """构建词汇表和IDF"""
        self.doc_count = len(documents)
        df = {}

        for doc in documents:
            tokens = simple_tokenizer(doc)
            unique_tokens = set(tokens)
            for token in unique_tokens:
                df[token] = df.get(token, 0) + 1

        # 计算IDF
        for token, doc_freq in df.items():
            self.idf[token] = math.log((self.doc_count + 1) / (doc_freq + 1)) + 1
            self.vocabulary[token] = len(self.vocabulary)

        self.fitted = True
        print(f"  [Vectorizer] 词汇表大小: {len(self.vocabulary)}")

    def transform(self, documents: List[str]) -> List[List[float]]:
        """转换为TF-IDF向量"""
        if not self.fitted:
            raise RuntimeError("Vectorizer not fitted yet")

        dim = len(self.vocabulary)
        vectors = []

        for doc in documents:
            tokens = simple_tokenizer(doc)
            # 计算词频
            tf = {}
            for token in tokens:
                tf[token] = tf.get(token, 0) + 1
            # 归一化
            total = len(tokens) if tokens else 1
            for token in tf:
                tf[token] /= total

            # 构建向量
            vector = [0.0] * dim
            for token, freq in tf.items():
                if token in self.vocabulary:
                    idx = self.vocabulary[token]
                    idf = self.idf.get(token, 1.0)
                    vector[idx] = freq * idf

            # 归一化
            norm = math.sqrt(sum(v * v for v in vector))
            if norm > 0:
                vector = [v / norm for v in vector]

            vectors.append(vector)

        return vectors

    def transform_one(self, document: str) -> List[float]:
        """转换单个文档"""
        return self.transform([document])[0]


# ===== 内存向量存储 =====

class InMemoryVectorStore:
    """简单的内存向量存储"""

    def __init__(self):
        self.chunks: List[ChunkData] = []
        self.vectors: List[List[float]] = []

    def add(self, chunks: List[ChunkData], vectors: List[List[float]]):
        """添加文档块和向量"""
        self.chunks = chunks
        self.vectors = vectors

    def search(self, query_vector: List[float], top_k: int = 5) -> List[Dict[str, Any]]:
        """简单的余弦相似度检索"""
        if not self.chunks or not self.vectors:
            return []

        # 计算相似度
        results = []
        for i, chunk in enumerate(self.chunks):
            similarity = cosine_similarity(query_vector, self.vectors[i])
            results.append({
                "chunk_id": chunk.chunk_id,
                "document_id": chunk.document_id,
                "content": chunk.content,
                "title": chunk.title,
                "score": similarity,
                "chunk_index": chunk.chunk_index,
            })

        # 排序并返回 top_k
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]


def cosine_similarity(a: List[float], b: List[float]) -> float:
    """
    计算余弦相似度 (Cosine Similarity)
    公式: cos(θ) = (A·B) / (||A|| * ||B||)

    其中:
    - A·B = sum(a_i * b_i) 点积 (dot product)
    - ||A|| = sqrt(sum(a_i^2)) 向量范数 (L2 norm)

    分数范围: -1 到 1
    - 1 表示完全相同方向
    - 0 表示正交（无相似）
    - -1 表示完全相反
    """
    dot_product = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(x * x for x in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot_product / (norm_a * norm_b)


# ===== BM25 实现 =====

class SimpleBM25:
    """
    简化版 BM25 实现
    基于 BM25 算法: score = IDF * (f * (k1 + 1)) / (f + k1 * (1 - b + b * (dl / avgdl)))
    """

    def __init__(self, k1: float = 1.5, b: float = 0.75):
        """
        Args:
            k1: 控制词频饱和度的参数 (1.2-2.0 通常效果较好)
            b: 控制文档长度归一化的参数 (0.75 是常用值)
        """
        self.k1 = k1
        self.b = b
        self.documents: List[str] = []
        self.tokenized_docs: List[List[str]] = []
        self.doc_freqs: Dict[str, int] = {}
        self.idf: Dict[str, float] = {}
        self.doc_lengths: List[int] = []
        self.avg_doc_length: float = 0.0
        self.total_docs: int = 0
        self.vocabulary: set = set()

    def fit(self, documents: List[str]):
        """构建 BM25 索引"""
        self.documents = documents
        self.total_docs = len(documents)

        # 分词
        self.tokenized_docs = [simple_tokenizer(doc) for doc in documents]

        # 计算文档长度
        self.doc_lengths = [len(tokens) for tokens in self.tokenized_docs]
        self.avg_doc_length = sum(self.doc_lengths) / self.total_docs if self.total_docs > 0 else 0

        # 计算文档频率 (DF)
        self.doc_freqs = {}
        for tokens in self.tokenized_docs:
            unique_terms = set(tokens)
            for term in unique_terms:
                self.doc_freqs[term] = self.doc_freqs.get(term, 0) + 1
                self.vocabulary.add(term)

        # 计算 IDF
        self.idf = {}
        for term, df in self.doc_freqs.items():
            # 使用 BM25 IDF 公式
            idf_val = math.log((self.total_docs - df + 0.5) / (df + 0.5) + 1.0)
            self.idf[term] = idf_val

        print(f"  [BM25] 文档数: {self.total_docs}, 词汇表大小: {len(self.vocabulary)}, 平均文档长度: {self.avg_doc_length:.2f}")

    def search(self, query: str, top_k: int = 10) -> List[Tuple[int, float]]:
        """
        搜索文档

        Returns:
            List[Tuple[int, float]]: (文档索引, 分数) 列表，按分数降序排列
        """
        query_tokens = simple_tokenizer(query)
        if not query_tokens:
            return []

        scores = [0.0] * self.total_docs

        for term in query_tokens:
            if term not in self.idf:
                continue

            idf = self.idf[term]

            for doc_idx, doc_tokens in enumerate(self.tokenized_docs):
                # 计算词频
                f = doc_tokens.count(term)
                if f == 0:
                    continue

                # 文档长度归一化
                dl = self.doc_lengths[doc_idx]
                norm_factor = 1 - self.b + self.b * (dl / self.avg_doc_length)

                # BM25 分数计算
                score = idf * (f * (self.k1 + 1)) / (f + self.k1 * norm_factor)
                scores[doc_idx] += score

        # 获取 Top-K
        indexed_scores = [(i, score) for i, score in enumerate(scores)]
        indexed_scores.sort(key=lambda x: x[1], reverse=True)

        return indexed_scores[:top_k]


class BM25Retriever:
    """BM25 检索器包装类"""

    def __init__(self, chunks: List[ChunkData], k1: float = 1.5, b: float = 0.75):
        self.chunks = chunks
        self.bm25 = SimpleBM25(k1=k1, b=b)
        # 使用 chunk 内容构建索引
        self.bm25.fit([c.content for c in chunks])

    def search(self, query: str, top_k: int = 10) -> List[Dict[str, Any]]:
        """检索并返回格式化的结果"""
        results = self.bm25.search(query, top_k)

        formatted_results = []
        for rank, (idx, score) in enumerate(results, 1):
            chunk = self.chunks[idx]
            formatted_results.append({
                "rank": rank,
                "chunk_id": chunk.chunk_id,
                "document_id": chunk.document_id,
                "content": chunk.content,
                "title": chunk.title,
                "score": score,
                "chunk_index": chunk.chunk_index,
            })

        return formatted_results


# ===== 混合检索 (向量 + BM25) =====

class HybridRetriever:
    """
    混合检索器: 融合向量检索和 BM25 的结果
    使用 RRF (Reciprocal Rank Fusion) 或加权融合
    """

    def __init__(
        self,
        vector_store: InMemoryVectorStore,
        bm25_retriever: BM25Retriever,
        vector_weight: float = 0.5,
        bm25_weight: float = 0.5,
        rrf_k: int = 60
    ):
        """
        Args:
            vector_store: 向量存储
            bm25_retriever: BM25 检索器
            vector_weight: 向量检索权重 (用于加权融合)
            bm25_weight: BM25 检索权重 (用于加权融合)
            rrf_k: RRF 融合参数
        """
        self.vector_store = vector_store
        self.bm25_retriever = bm25_retriever
        self.vector_weight = vector_weight
        self.bm25_weight = bm25_weight
        self.rrf_k = rrf_k

    def search_rrf(self, query: str, query_vector: List[float], top_k: int = 10) -> List[Dict[str, Any]]:
        """
        使用 RRF (Reciprocal Rank Fusion) 融合两种检索结果
        RRF 公式: score = sum(1 / (k + rank))
        """
        # 获取向量检索结果
        vector_results = self.vector_store.search(query_vector, top_k=top_k * 2)

        # 获取 BM25 检索结果
        bm25_results = self.bm25_retriever.search(query, top_k=top_k * 2)

        # 构建 chunk_id -> rank 映射
        vector_ranks = {r["chunk_id"]: rank for rank, r in enumerate(vector_results, 1)}
        bm25_ranks = {r["chunk_id"]: rank for rank, r in enumerate(bm25_results, 1)}

        # 获取所有候选 chunk_ids
        all_chunk_ids = set(vector_ranks.keys()) | set(bm25_ranks.keys())

        # 计算 RRF 分数
        rrf_scores = {}
        for chunk_id in all_chunk_ids:
            score = 0.0
            if chunk_id in vector_ranks:
                score += 1.0 / (self.rrf_k + vector_ranks[chunk_id])
            if chunk_id in bm25_ranks:
                score += 1.0 / (self.rrf_k + bm25_ranks[chunk_id])
            rrf_scores[chunk_id] = score

        # 排序并获取 Top-K
        sorted_results = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)[:top_k]

        # 构建 chunk_id -> chunk 的映射
        chunk_map = {c.chunk_id: c for c in self.bm25_retriever.chunks}

        formatted_results = []
        for rank, (chunk_id, score) in enumerate(sorted_results, 1):
            chunk = chunk_map.get(chunk_id)
            if chunk:
                formatted_results.append({
                    "rank": rank,
                    "chunk_id": chunk.chunk_id,
                    "document_id": chunk.document_id,
                    "content": chunk.content,
                    "title": chunk.title,
                    "score": score,
                    "chunk_index": chunk.chunk_index,
                    "source": self._get_source(chunk_id, vector_ranks, bm25_ranks)
                })

        return formatted_results

    def search_weighted(
        self,
        query: str,
        query_vector: List[float],
        top_k: int = 10,
        vector_top_k: int = 50
    ) -> List[Dict[str, Any]]:
        """
        使用加权融合两种检索结果
        需要归一化分数后再加权
        """
        # 获取向量检索结果 (获取更多用于融合)
        vector_results = self.vector_store.search(query_vector, top_k=vector_top_k)

        # 获取 BM25 检索结果
        bm25_results = self.bm25_retriever.search(query, top_k=vector_top_k)

        # 归一化向量分数 (余弦相似度范围 [-1, 1]，通常实际为 [0, 1])
        vector_scores = {}
        if vector_results:
            max_score = max(r["score"] for r in vector_results)
            min_score = min(r["score"] for r in vector_results)
            score_range = max_score - min_score if max_score > min_score else 1.0
            for r in vector_results:
                vector_scores[r["chunk_id"]] = (r["score"] - min_score) / score_range

        # 归一化 BM25 分数
        bm25_scores = {}
        if bm25_results:
            max_score = max(r["score"] for r in bm25_results)
            min_score = min(r["score"] for r in bm25_results)
            score_range = max_score - min_score if max_score > min_score else 1.0
            for r in bm25_results:
                bm25_scores[r["chunk_id"]] = (r["score"] - min_score) / score_range

        # 获取所有候选 chunk_ids
        all_chunk_ids = set(vector_scores.keys()) | set(bm25_scores.keys())

        # 计算加权分数
        weighted_scores = {}
        for chunk_id in all_chunk_ids:
            v_score = vector_scores.get(chunk_id, 0.0) * self.vector_weight
            b_score = bm25_scores.get(chunk_id, 0.0) * self.bm25_weight
            weighted_scores[chunk_id] = v_score + b_score

        # 排序并获取 Top-K
        sorted_results = sorted(weighted_scores.items(), key=lambda x: x[1], reverse=True)[:top_k]

        # 构建 chunk_id -> chunk 的映射
        chunk_map = {c.chunk_id: c for c in self.bm25_retriever.chunks}

        formatted_results = []
        for rank, (chunk_id, score) in enumerate(sorted_results, 1):
            chunk = chunk_map.get(chunk_id)
            if chunk:
                formatted_results.append({
                    "rank": rank,
                    "chunk_id": chunk.chunk_id,
                    "document_id": chunk.document_id,
                    "content": chunk.content,
                    "title": chunk.title,
                    "score": score,
                    "chunk_index": chunk.chunk_index,
                    "source": self._get_source(chunk_id, vector_scores, bm25_scores)
                })

        return formatted_results

    def _get_source(self, chunk_id: str, vector_dict: Dict, bm25_dict: Dict) -> str:
        """判断结果来源"""
        in_vector = chunk_id in vector_dict
        in_bm25 = chunk_id in bm25_dict
        if in_vector and in_bm25:
            return "hybrid"
        elif in_vector:
            return "vector"
        else:
            return "bm25"


# ===== 召回率评估 =====

def calculate_recall_at_k(
    retrieved_docs: List[str],
    relevant_docs: List[str],
    k: int
) -> float:
    """计算 Recall@K"""
    if not relevant_docs:
        return 0.0

    retrieved_k = retrieved_docs[:k]
    relevant_retrieved = len([doc for doc in retrieved_k if doc in relevant_docs])
    return relevant_retrieved / len(relevant_docs)


def calculate_mrr(retrieved_docs: List[str], relevant_docs: List[str]) -> float:
    """计算平均倒数排名 (MRR)"""
    for i, doc in enumerate(retrieved_docs, 1):
        if doc in relevant_docs:
            return 1.0 / i
    return 0.0


def calculate_precision_at_k(
    retrieved_docs: List[str],
    relevant_docs: List[str],
    k: int
) -> float:
    """计算 Precision@K"""
    if k == 0:
        return 0.0

    retrieved_k = retrieved_docs[:k]
    relevant_retrieved = len([doc for doc in retrieved_k if doc in relevant_docs])
    return relevant_retrieved / k


def evaluate_retrieval(
    test_cases: List[TestCase],
    store: InMemoryVectorStore,
    vectorizer: SimpleTFIDFVectorizer,
    top_k: int = 5
) -> Dict[str, Any]:
    """评估检索系统"""
    results = []

    for test_case in test_cases:
        # 编码查询
        query_vector = vectorizer.transform_one(test_case.question)

        # 检索
        retrieved = store.search(query_vector, top_k=top_k)

        # 提取检索到的文档ID
        retrieved_doc_ids = [r["document_id"] for r in retrieved]

        # 计算指标
        recall = calculate_recall_at_k(retrieved_doc_ids, test_case.relevant_docs, top_k)
        precision = calculate_precision_at_k(retrieved_doc_ids, test_case.relevant_docs, top_k)
        mrr = calculate_mrr(retrieved_doc_ids, test_case.relevant_docs)

        # 保存完整检索结果（Top 5）
        results.append({
            "question": test_case.question,
            "ground_truth": test_case.ground_truth,
            # Top 5 检索结果详情
            "retrieved_top5": [
                {
                    "rank": i + 1,
                    "chunk_id": r["chunk_id"],
                    "document_id": r["document_id"],
                    "title": r["title"],
                    "score": round(r["score"], 4),
                    "content_preview": r["content"][:200] + "..." if len(r["content"]) > 200 else r["content"]
                }
                for i, r in enumerate(retrieved)
            ],
            "retrieved_doc_ids": retrieved_doc_ids,
            "relevant_docs": test_case.relevant_docs,
            "recall": recall,
            "precision": precision,
            "mrr": mrr,
        })

    # 计算平均值
    avg_recall = sum(r["recall"] for r in results) / len(results)
    avg_precision = sum(r["precision"] for r in results) / len(results)
    avg_mrr = sum(r["mrr"] for r in results) / len(results)

    return {
        "results": results,
        "metrics": {
            "recall_at_k": round(avg_recall, 4),
            "precision_at_k": round(avg_precision, 4),
            "mrr": round(avg_mrr, 4),
        }
    }


# ===== 文档加载 =====

def load_markdown_files(directory: str) -> Dict[str, tuple]:
    """
    加载 Markdown 文件

    Returns:
        Dict[str, tuple]: {文档ID: (标题, 内容)}
    """
    docs = {}
    dir_path = Path(directory)

    if not dir_path.exists():
        print(f"❌ 目录不存在: {directory}")
        return docs

    for md_file in dir_path.glob("*.md"):
        try:
            with open(md_file, "r", encoding="utf-8") as f:
                content = f.read()
                # 提取文档ID
                doc_name = md_file.stem.replace("MinerU_markdown_", "")
                # 提取标题
                title = extract_title_from_content(content) or doc_name
                docs[doc_name] = (title, content)
                print(f"  ✓ 加载: {md_file.name} ({len(content)} 字符)")
        except Exception as e:
            print(f"  ✗ 加载失败 {md_file.name}: {e}")

    print(f"\n📚 总计加载: {len(docs)} 个文档")
    return docs


def extract_title_from_content(content: str) -> Optional[str]:
    """从Markdown内容中提取标题"""
    lines = content.split("\n")
    for line in lines[:10]:
        line = line.strip()
        if line.startswith("# "):
            return line[2:].strip()
    return None


# ===== 主流程 =====

def run_recall_test():
    """运行召回率测试"""

    print("\n" + "=" * 60)
    print("RAG 召回率测试 (TF-IDF)")
    print("=" * 60)

    # 1. 加载 Markdown 文档
    print("\n[1/5] 加载 Markdown 文档...")
    docs = load_markdown_files(MARKDOWN_DIR)
    if not docs:
        print("❌ 没有找到文档")
        return

    # 2. 分块
    print("\n[2/5] 文档分块...")
    # 使用真实的 DocumentChunker
    chunker = DocumentChunker(
        chunk_size=512,
        chunk_overlap=50,
        min_chunk_size=100
    )
    all_chunks = []

    for doc_id, (title, content) in docs.items():
        pages = [{"page_number": 1, "content": content}]
        chunks = chunker.chunk(doc_id, content, pages, strategy="semantic")
        # 转换为 ChunkData 格式
        for chunk in chunks:
            all_chunks.append(ChunkData(
                chunk_id=chunk.id,
                document_id=chunk.document_id,
                content=chunk.content,
                title=title,
                chunk_index=chunk.chunk_index,
                page_number=chunk.page_number,
                section=chunk.section,
            ))
        print(f"  - {doc_id}: {len(chunks)} 个 chunks")

    print(f"\n📦 总计 chunks: {len(all_chunks)}")

    # 3. 向量化
    print("\n[3/5] 向量化...")
    vectorizer = SimpleTFIDFVectorizer()

    # 准备文档内容
    doc_contents = [chunk.content for chunk in all_chunks]

    # Fit and transform
    vectorizer.fit(doc_contents)
    vectors = vectorizer.transform(doc_contents)

    print(f"  - 向量维度: {len(vectors[0]) if vectors else 0}")

    # 4. 存储到向量数据库
    print("\n[4/5] 存储到向量存储...")
    store = InMemoryVectorStore()
    store.add(all_chunks, vectors)
    print(f"  - 存储了 {len(all_chunks)} 个向量")

    # 5. 评估召回率
    print("\n[5/5] 评估召回率...")
    top_k = 5
    eval_results = evaluate_retrieval(TEST_CASES, store, vectorizer, top_k=top_k)

    # 打印结果
    print("\n" + "=" * 60)
    print("评估结果")
    print("=" * 60)

    print(f"\n📊 平均指标 (Top-{top_k}):")
    print(f"   Recall@{top_k}:   {eval_results['metrics']['recall_at_k']:.4f}")
    print(f"   Precision@{top_k}: {eval_results['metrics']['precision_at_k']:.4f}")
    print(f"   MRR:           {eval_results['metrics']['mrr']:.4f}")

    print("\n📋 详细结果:")
    for i, result in enumerate(eval_results["results"], 1):
        print(f"\n{'='*60}")
        print(f"--- 测试用例 {i}: {result['question']}")
        print(f"{'='*60}")
        print(f"标准答案(Ground Truth): {result['ground_truth']}")
        print(f"相关文档: {result['relevant_docs']}")

        print(f"\n🔍 Top 5 检索结果:")
        for item in result["retrieved_top5"]:
            print(f"\n  [{item['rank']}] 文档ID: {item['document_id']}")
            print(f"      标题: {item['title']}")
            print(f"      相似度得分: {item['score']:.4f}")
            print(f"      内容预览: {item['content_preview'][:150]}...")

        print(f"\n指标: Recall@{top_k}: {result['recall']:.4f} | Precision@{top_k}: {result['precision']:.4f} | MRR: {result['mrr']:.4f}")

    # 保存结果
    output_file = "backend/tests/recall_test_results.json"
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(eval_results, f, ensure_ascii=False, indent=2)
    print(f"\n✅ 结果已保存到: {output_file}")

    return eval_results


# ===== 测试不同分块策略 =====

def test_different_chunk_sizes():
    """测试不同的 chunk size"""

    docs = load_markdown_files(MARKDOWN_DIR)
    chunk_sizes = [300, 500, 800]
    results = {}

    for chunk_size in chunk_sizes:
        print(f"\n{'='*60}")
        print(f"测试 chunk_size: {chunk_size}")
        print(f"{'='*60}")

        # 分块
        # 使用真实的 DocumentChunker
        chunker = DocumentChunker(
            chunk_size=chunk_size,
            chunk_overlap=50,
            min_chunk_size=100
        )
        all_chunks = []
        for doc_id, (title, content) in docs.items():
            pages = [{"page_number": 1, "content": content}]
            chunks = chunker.chunk(doc_id, content, pages, strategy="semantic")
            # 转换为 ChunkData 格式
            for chunk in chunks:
                all_chunks.append(ChunkData(
                    chunk_id=chunk.id,
                    document_id=chunk.document_id,
                    content=chunk.content,
                    title=title,
                    chunk_index=chunk.chunk_index,
                    page_number=chunk.page_number,
                    section=chunk.section,
                ))

        print(f"  chunks数量: {len(all_chunks)}")

        # 向量化
        vectorizer = SimpleTFIDFVectorizer()
        doc_contents = [chunk.content for chunk in all_chunks]
        vectorizer.fit(doc_contents)
        vectors = vectorizer.transform(doc_contents)

        # 存储
        store = InMemoryVectorStore()
        store.add(all_chunks, vectors)

        # 评估
        eval_results = evaluate_retrieval(TEST_CASES, store, vectorizer, top_k=5)
        results[chunk_size] = eval_results["metrics"]

        print(f"\n结果:")
        print(f"  Recall@5: {eval_results['metrics']['recall_at_k']:.4f}")
        print(f"  Precision@5: {eval_results['metrics']['precision_at_k']:.4f}")
        print(f"  MRR: {eval_results['metrics']['mrr']:.4f}")

    # 打印对比结果
    print("\n" + "=" * 60)
    print("Chunk Size 对比结果")
    print("=" * 60)
    print(f"{'Chunk Size':<15} {'Recall@5':<12} {'Precision@5':<12} {'MRR':<12}")
    print("-" * 51)
    for chunk_size, metrics in results.items():
        print(f"{chunk_size:<15} {metrics['recall_at_k']:<12.4f} {metrics['precision_at_k']:<12.4f} {metrics['mrr']:<12.4f}")

    return results


# ===== Milvus 真实数据库测试 =====

def run_recall_test_with_milvus(collection_name: str = "enterprise_documents", recreate: bool = False):
    """使用真实 Milvus 云端数据库进行召回率测试"""

    print("\n" + "=" * 60)
    print("RAG 召回率测试 (真实 Milvus)")
    print("=" * 60)

    # 1. 加载 Markdown 文档
    print("\n[1/6] 加载 Markdown 文档...")
    docs = load_markdown_files(MARKDOWN_DIR)
    if not docs:
        print("❌ 没有找到文档")
        return

    # 2. 分块
    print("\n[2/6] 文档分块...")
    # 使用真实的 DocumentChunker
    chunker = DocumentChunker(
        chunk_size=512,
        chunk_overlap=50,
        min_chunk_size=100
    )
    all_chunks = []

    for doc_id, (title, content) in docs.items():
        pages = [{"page_number": 1, "content": content}]
        chunks = chunker.chunk(doc_id, content, pages, strategy="semantic")
        # 转换为 ChunkData 格式
        for chunk in chunks:
            all_chunks.append(ChunkData(
                chunk_id=chunk.id,
                document_id=chunk.document_id,
                content=chunk.content,
                title=title,
                chunk_index=chunk.chunk_index,
                page_number=chunk.page_number,
                section=chunk.section,
            ))
        print(f"  - {doc_id}: {len(chunks)} 个 chunks")

    print(f"\n📦 总计 chunks: {len(all_chunks)}")

    # 3. 向量化 - 使用项目的 embedding 模型
    print("\n[3/6] 向量化 (BGE-M3)...")
    try:
        # 尝试使用项目的 embedding
        from app.rag.embedding import encode_text as app_encode_text

        # 批量获取 embedding
        texts = [chunk.content for chunk in all_chunks]
        embeddings = app_encode_text(texts)

        # 转换为 list
        if hasattr(embeddings, 'tolist'):
            embeddings = embeddings.tolist()

        print(f"  ✓ 使用 BGE-M3 向量化完成，维度: {len(embeddings[0])}")
    except ImportError as e:
        print(f"  ⚠️ 无法导入项目 embedding ({e})，使用 TF-IDF")
        # 回退到 TF-IDF
        vectorizer = SimpleTFIDFVectorizer()
        doc_contents = [chunk.content for chunk in all_chunks]
        vectorizer.fit(doc_contents)
        embeddings = vectorizer.transform(doc_contents)

    # 4. 连接 Milvus
    print("\n[4/6] 连接 Milvus 云端数据库...")
    from app.integrations.milvus_client import get_milvus_client
    from app.config import settings

    milvus_client = get_milvus_client()
    milvus_client.connect()

    print(f"  - URI: {settings.MILVUS_CLOUD_URI}")
    print(f"  - Collection: {collection_name}")

    # 5. 创建 Collection 并插入数据
    print("\n[5/6] 创建 Collection 并插入数据...")

    has_data = False

    # 检查是否需要重建
    if milvus_client.client.has_collection(collection_name):
        if recreate:
            print(f"  - 删除已有 collection: {collection_name}")
            milvus_client.client.drop_collection(collection_name)
            has_data = True
        else:
            print(f"  - Collection 已存在，跳过插入")
            has_data = False
    else:
        has_data = True

    if has_data:
        # 获取实际的向量维度
        actual_dim = len(embeddings[0]) if embeddings else 1024
        print(f"  - 向量维度: {actual_dim}")

        # 更新 Milvus 配置的维度
        milvus_client.dimension = actual_dim
        milvus_client.collection_name = collection_name

        # 先创建 Collection
        print(f"  - 创建 Collection: {collection_name} (dim={actual_dim})")
        milvus_client.create_collection(overwrite=True)

        # 准备插入数据
        import time
        milvus_data = []
        for i, (chunk, embedding) in enumerate(zip(all_chunks, embeddings)):
            milvus_data.append({
                "chunk_id": chunk.chunk_id,
                "document_id": chunk.document_id,
                "content": chunk.content,
                "title": chunk.title,
                "department_id": "",
                "is_public": True,
                "allowed_roles": [],
                "page_number": chunk.page_number or 0,
                "section": chunk.section or "",
                "chunk_index": chunk.chunk_index,
                "created_at": int(time.time()),
                "embedding": embedding,
            })

        # 插入数据
        print(f"  - 插入 {len(milvus_data)} 条数据...")
        milvus_client.insert_chunks(milvus_data)
        print(f"  ✓ 数据插入完成")

    # 6. 执行检索测试
    print("\n[6/6] 执行检索测试...")

    # 使用 TF-IDF 作为查询向量化的回退
    vectorizer = SimpleTFIDFVectorizer()
    doc_contents = [chunk.content for chunk in all_chunks]
    vectorizer.fit(doc_contents)

    # 尝试使用项目 embedding
    try:
        from app.rag.embedding import encode_query as app_encode_query
        use_app_embedding = True
    except ImportError:
        use_app_embedding = False

    # 评估每个测试用例
    results = []
    for test_case in TEST_CASES:
        # 向量化查询
        if use_app_embedding:
            try:
                query_embedding = app_encode_query(test_case.question)
            except:
                query_embedding = vectorizer.transform_one(test_case.question)
        else:
            query_embedding = vectorizer.transform_one(test_case.question)

        # 转换为 list
        if hasattr(query_embedding, 'tolist'):
            query_embedding = query_embedding.tolist()

        # 检索
        milvus_results = milvus_client.search(
            query_embedding=query_embedding,
            top_k=5
        )

        # 提取检索到的文档ID
        retrieved_doc_ids = [r["document_id"] for r in milvus_results]

        # 计算指标
        recall = calculate_recall_at_k(retrieved_doc_ids, test_case.relevant_docs, 5)
        precision = calculate_precision_at_k(retrieved_doc_ids, test_case.relevant_docs, 5)
        mrr = calculate_mrr(retrieved_doc_ids, test_case.relevant_docs)

        # 保存完整检索结果
        results.append({
            "question": test_case.question,
            "ground_truth": test_case.ground_truth,
            "retrieved_top5": [
                {
                    "rank": i + 1,
                    "chunk_id": r["chunk_id"],
                    "document_id": r["document_id"],
                    "title": r["title"],
                    "score": round(r["score"], 4),
                    "content_preview": r["content"][:200] + "..." if len(r["content"]) > 200 else r["content"]
                }
                for i, r in enumerate(milvus_results)
            ],
            "retrieved_doc_ids": retrieved_doc_ids,
            "relevant_docs": test_case.relevant_docs,
            "recall": recall,
            "precision": precision,
            "mrr": mrr,
        })

        print(f"  ✓ {test_case.question[:30]}... -> Recall: {recall:.2f}")

    # 计算平均值
    avg_recall = sum(r["recall"] for r in results) / len(results)
    avg_precision = sum(r["precision"] for r in results) / len(results)
    avg_mrr = sum(r["mrr"] for r in results) / len(results)

    eval_results = {
        "results": results,
        "metrics": {
            "recall_at_k": round(avg_recall, 4),
            "precision_at_k": round(avg_precision, 4),
            "mrr": round(avg_mrr, 4),
        }
    }

    # 打印结果
    print("\n" + "=" * 60)
    print("评估结果 (Milvus)")
    print("=" * 60)

    print(f"\n📊 平均指标 (Top-5):")
    print(f"   Recall@5:   {eval_results['metrics']['recall_at_k']:.4f}")
    print(f"   Precision@5: {eval_results['metrics']['precision_at_k']:.4f}")
    print(f"   MRR:           {eval_results['metrics']['mrr']:.4f}")

    print("\n📋 详细结果:")
    for i, result in enumerate(eval_results["results"], 1):
        print(f"\n{'='*60}")
        print(f"--- 测试用例 {i}: {result['question']}")
        print(f"{'='*60}")
        print(f"标准答案: {result['ground_truth']}")
        print(f"相关文档: {result['relevant_docs']}")

        print(f"\n🔍 Top 5 检索结果:")
        for item in result["retrieved_top5"]:
            print(f"\n  [{item['rank']}] 文档ID: {item['document_id']}")
            print(f"      标题: {item['title']}")
            print(f"      相似度得分: {item['score']:.4f}")

        print(f"\n指标: Recall@5: {result['recall']:.4f} | Precision@5: {result['precision']:.4f} | MRR: {result['mrr']:.4f}")

    # 保存结果
    output_file = "backend/tests/recall_test_results_milvus.json"
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(eval_results, f, ensure_ascii=False, indent=2)
    print(f"\n✅ 结果已保存到: {output_file}")

    return eval_results


def load_ground_truth_dataset(json_path: str) -> Dict[str, Any]:
    """加载 Ground Truth 数据集"""
    import json
    from pathlib import Path

    path = Path(json_path)
    if not path.exists():
        print(f"❌ Ground truth 文件不存在: {json_path}")
        return {}

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    print(f"  ✓ 加载 ground truth: {json_path}")
    print(f"    - chunk_level: {data.get('stats', {}).get('chunk_level_count', 0)} 条")
    print(f"    - answer_level: {data.get('stats', {}).get('answer_level_count', 0)} 条")
    return data


def run_recall_test_with_ground_truth(
    ground_truth_path: str = "tests/ground_truth/ground_truth_auto_dataset.json",
    top_k: int = 5,
    mode: str = "memory"
):
    """
    使用 Ground Truth 数据集进行召回率测试

    Args:
        ground_truth_path: ground truth JSON 文件路径
        top_k: 检索 Top-K
        mode: 检索模式 (memory=内存TF-IDF, milvus=真实Milvus)
    """
    print("\n" + "=" * 60)
    print("RAG 召回率测试 (基于 Ground Truth 数据集)")
    print("=" * 60)

    # 1. 加载 Ground Truth 数据
    print("\n[1/5] 加载 Ground Truth 数据集...")
    gt_data = load_ground_truth_dataset(ground_truth_path)
    if not gt_data:
        return

    chunk_level_cases = gt_data.get("chunk_level", [])
    if not chunk_level_cases:
        print("⚠️ chunk_level 数据为空，无法评测")
        return

    # 2. 加载 Markdown 文档
    print("\n[2/5] 加载 Markdown 文档...")
    docs = load_markdown_files(MARKDOWN_DIR)
    if not docs:
        print("❌ 没有找到文档")
        return

    # 3. 文档分块（必须与生成 ground truth 时的逻辑一致）
    print("\n[3/5] 文档分块...")
    # 从 ground truth meta 中获取分块参数
    chunk_size = gt_data.get("meta", {}).get("chunk_size", 512)
    chunk_overlap = gt_data.get("meta", {}).get("chunk_overlap", 50)

    # 使用真实的 DocumentChunker
    chunker = DocumentChunker(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        min_chunk_size=min_chunk_size
    )
    all_chunks = []

    for doc_id, (title, content) in docs.items():
        pages = [{"page_number": 1, "content": content}]
        strategy = gt_data.get("meta", {}).get("chunk_strategy", "semantic")
        chunks = chunker.chunk(doc_id, content, pages, strategy=strategy)
        # 转换为 ChunkData 格式
        for chunk in chunks:
            all_chunks.append(ChunkData(
                chunk_id=chunk.id,
                document_id=chunk.document_id,
                content=chunk.content,
                title=title,
                chunk_index=chunk.chunk_index,
                page_number=chunk.page_number,
                section=chunk.section,
            ))

    print(f"\n📦 总计 chunks: {len(all_chunks)}")

    # 建立 chunk_id -> chunk 的映射
    chunk_map = {c.chunk_id: c for c in all_chunks}

    # 4. 根据模式选择检索方式
    print(f"\n[4/5] 初始化检索器 (mode={mode})...")

    if mode == "milvus":
        # Milvus 模式
        try:
            from app.integrations.milvus_client import get_milvus_client
            from app.config import settings

            milvus_client = get_milvus_client()
            milvus_client.connect()
            print(f"  ✓ 已连接 Milvus: {settings.MILVUS_CLOUD_URI}")

            # 使用项目的 embedding 模型
            try:
                from app.rag.embedding import encode_query
                def get_query_vector(query: str):
                    emb = encode_query(query)
                    return emb.tolist() if hasattr(emb, 'tolist') else emb
            except ImportError:
                print("  ⚠️ 无法导入 encode_query，使用 TF-IDF 作为 fallback")
                vectorizer = SimpleTFIDFVectorizer()
                doc_contents = [c.content for c in all_chunks]
                vectorizer.fit(doc_contents)
                def get_query_vector(query: str):
                    return vectorizer.transform_one(query)

            def retrieve_fn(query: str, top_k: int) -> List[Dict]:
                query_vector = get_query_vector(query)
                return milvus_client.search(query_embedding=query_vector, top_k=top_k)

        except Exception as e:
            print(f"❌ Milvus 连接失败: {e}")
            return
    else:
        # 内存 TF-IDF 模式
        vectorizer = SimpleTFIDFVectorizer()
        doc_contents = [c.content for c in all_chunks]
        vectorizer.fit(doc_contents)
        vectors = vectorizer.transform(doc_contents)

        store = InMemoryVectorStore()
        store.add(all_chunks, vectors)
        print(f"  ✓ 内存向量存储已创建: {len(all_chunks)} 个向量")

        def retrieve_fn(query: str, top_k: int) -> List[Dict]:
            query_vector = vectorizer.transform_one(query)
            return store.search(query_vector, top_k=top_k)

    # 5. 执行评估
    print(f"\n[5/5] 执行评估 (Top-{top_k})...")

    results = []
    metrics_accumulator = {
        "hit_rate": [],
        "recall": [],
        "precision": [],
        "mrr": [],
    }

    for i, case in enumerate(chunk_level_cases, 1):
        query = case["question"]
        relevant_chunk_ids = set(case["relevant_chunk_ids"])
        ground_truth_answer = case.get("ground_truth", "")

        # 执行检索
        retrieved = retrieve_fn(query, top_k)
        retrieved_chunk_ids = [r["chunk_id"] for r in retrieved]

        # 计算指标
        # Hit Rate@K: Top-K 中至少命中 1 个
        hit = int(any(rid in relevant_chunk_ids for rid in retrieved_chunk_ids))
        metrics_accumulator["hit_rate"].append(hit)

        # Recall@K: ground truth 中有多少被召回
        recalled = len(set(retrieved_chunk_ids) & relevant_chunk_ids)
        recall = recalled / len(relevant_chunk_ids) if relevant_chunk_ids else 0.0
        metrics_accumulator["recall"].append(recall)

        # Precision@K: Top-K 中有多少是相关的
        precision = recalled / top_k
        metrics_accumulator["precision"].append(precision)

        # MRR: 第一个相关文档的排名倒数
        mrr = 0.0
        for rank, rid in enumerate(retrieved_chunk_ids, 1):
            if rid in relevant_chunk_ids:
                mrr = 1.0 / rank
                break
        metrics_accumulator["mrr"].append(mrr)

        # 保存详细结果
        results.append({
            "query_id": case.get("query_id", f"q{i}"),
            "question": query,
            "ground_truth_answer": ground_truth_answer,
            "relevant_chunk_ids": list(relevant_chunk_ids),
            "retrieved_topk": [
                {
                    "rank": j + 1,
                    "chunk_id": r["chunk_id"],
                    "document_id": r["document_id"],
                    "title": r["title"],
                    "score": round(r.get("score", 0), 4),
                    "content_preview": r.get("content", "")[:200] + "..." if len(r.get("content", "")) > 200 else r.get("content", "")
                }
                for j, r in enumerate(retrieved)
            ],
            "metrics": {
                "hit": hit,
                "recall": round(recall, 4),
                "precision": round(precision, 4),
                "mrr": round(mrr, 4),
            }
        })

        if i % 10 == 0 or i == len(chunk_level_cases):
            print(f"  - 进度: {i}/{len(chunk_level_cases)}")

    # 计算平均指标
    avg_metrics = {
        f"hit_rate@{top_k}": round(sum(metrics_accumulator["hit_rate"]) / len(metrics_accumulator["hit_rate"]), 4),
        f"recall@{top_k}": round(sum(metrics_accumulator["recall"]) / len(metrics_accumulator["recall"]), 4),
        f"precision@{top_k}": round(sum(metrics_accumulator["precision"]) / len(metrics_accumulator["precision"]), 4),
        "mrr": round(sum(metrics_accumulator["mrr"]) / len(metrics_accumulator["mrr"]), 4),
    }

    # 打印结果
    print("\n" + "=" * 60)
    print("评估结果")
    print("=" * 60)

    print(f"\n📊 平均指标 (Top-{top_k}):")
    for k, v in avg_metrics.items():
        print(f"   {k}: {v:.4f}")

    print(f"\n📋 详细结果 ({len(results)} 个测试用例):")
    for i, result in enumerate(results, 1):
        print(f"\n{'='*60}")
        print(f"--- 测试用例 {i}: {result['question'][:50]}...")
        print(f"{'='*60}")
        print(f"标准答案: {result['ground_truth_answer'][:100]}...")
        print(f"相关 chunk_ids: {result['relevant_chunk_ids']}")

        print(f"\n🔍 Top {top_k} 检索结果:")
        for item in result["retrieved_topk"]:
            match_marker = "✓" if item["chunk_id"] in result["relevant_chunk_ids"] else "✗"
            print(f"  [{item['rank']}] {match_marker} {item['chunk_id'][:50]}...")
            print(f"      相似度: {item['score']:.4f} | 标题: {item['title'][:40]}...")

        m = result["metrics"]
        print(f"\n指标: Hit: {m['hit']} | Recall@{top_k}: {m['recall']:.4f} | Precision@{top_k}: {m['precision']:.4f} | MRR: {m['mrr']:.4f}")

    # 保存结果
    output_data = {
        "meta": {
            "mode": mode,
            "top_k": top_k,
            "ground_truth_path": ground_truth_path,
            "total_cases": len(results),
            **avg_metrics
        },
        "results": results
    }

    output_file = f"backend/tests/recall_test_results_gt_{mode}.json"
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    print(f"\n✅ 结果已保存到: {output_file}")

    return output_data


def compare_retrieval_methods(
    ground_truth_path: str = "tests/ground_truth/ground_truth_auto_dataset.json",
    top_k: int = 5,
    fusion_method: str = "rrf",
    vector_weight: float = 0.5,
    bm25_weight: float = 0.5,
    rrf_k: int = 60
):
    """
    对比三种检索方式：向量检索、BM25、混合检索

    Args:
        ground_truth_path: ground truth JSON 文件路径
        top_k: 检索 Top-K
        fusion_method: 融合方法 ("rrf" 或 "weighted")
        vector_weight: 向量检索权重 (用于 weighted 融合)
        bm25_weight: BM25 检索权重 (用于 weighted 融合)
        rrf_k: RRF 融合参数
    """
    print("\n" + "=" * 80)
    print("三种检索方式对比: 向量检索 vs BM25 vs 混合检索")
    print("=" * 80)

    # 1. 加载 Ground Truth 数据
    print("\n[1/5] 加载 Ground Truth 数据集...")
    gt_data = load_ground_truth_dataset(ground_truth_path)
    if not gt_data:
        return

    chunk_level_cases = gt_data.get("chunk_level", [])
    if not chunk_level_cases:
        print("⚠️ chunk_level 数据为空，无法评测")
        return

    # 2. 加载 Markdown 文档
    print("\n[2/5] 加载 Markdown 文档...")
    docs = load_markdown_files(MARKDOWN_DIR)
    if not docs:
        print("❌ 没有找到文档")
        return

    # 3. 文档分块
    print("\n[3/5] 文档分块...")
    chunk_size = gt_data.get("meta", {}).get("chunk_size", 512)
    chunk_overlap = gt_data.get("meta", {}).get("chunk_overlap", 50)

    # 使用真实的 DocumentChunker
    chunker = DocumentChunker(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        min_chunk_size=min_chunk_size
    )
    all_chunks = []

    for doc_id, (title, content) in docs.items():
        pages = [{"page_number": 1, "content": content}]
        strategy = gt_data.get("meta", {}).get("chunk_strategy", "semantic")
        chunks = chunker.chunk(doc_id, content, pages, strategy=strategy)
        # 转换为 ChunkData 格式
        for chunk in chunks:
            all_chunks.append(ChunkData(
                chunk_id=chunk.id,
                document_id=chunk.document_id,
                content=chunk.content,
                title=title,
                chunk_index=chunk.chunk_index,
                page_number=chunk.page_number,
                section=chunk.section,
            ))

    print(f"\n📦 总计 chunks: {len(all_chunks)}")

    # 建立 chunk_id -> chunk 的映射
    chunk_map = {c.chunk_id: c for c in all_chunks}

    # 4. 初始化三种检索器
    print("\n[4/5] 初始化三种检索器...")

    # 4.1 向量检索器 (TF-IDF)
    print("  - 初始化向量检索器 (TF-IDF)...")
    vectorizer = SimpleTFIDFVectorizer()
    doc_contents = [c.content for c in all_chunks]
    vectorizer.fit(doc_contents)
    vectors = vectorizer.transform(doc_contents)

    vector_store = InMemoryVectorStore()
    vector_store.add(all_chunks, vectors)

    # 4.2 BM25 检索器
    print("  - 初始化 BM25 检索器...")
    bm25_retriever = BM25Retriever(all_chunks, k1=1.5, b=0.75)

    # 4.3 混合检索器
    print(f"  - 初始化混合检索器 (fusion={fusion_method})...")
    hybrid_retriever = HybridRetriever(
        vector_store=vector_store,
        bm25_retriever=bm25_retriever,
        vector_weight=vector_weight,
        bm25_weight=bm25_weight,
        rrf_k=rrf_k
    )

    print(f"    ✓ 三种检索器就绪")

    # 5. 执行对比评估
    print(f"\n[5/5] 执行对比评估 (Top-{top_k})...")

    # 定义三种检索函数
    def vector_search(query: str, k: int) -> List[Dict]:
        query_vector = vectorizer.transform_one(query)
        return vector_store.search(query_vector, top_k=k)

    def bm25_search(query: str, k: int) -> List[Dict]:
        return bm25_retriever.search(query, top_k=k)

    def hybrid_search(query: str, k: int) -> List[Dict]:
        query_vector = vectorizer.transform_one(query)
        if fusion_method == "rrf":
            return hybrid_retriever.search_rrf(query, query_vector, top_k=k)
        else:
            return hybrid_retriever.search_weighted(query, query_vector, top_k=k)

    # 评估函数
    def evaluate_case(case: Dict, retrieved: List[Dict], method_name: str) -> Dict:
        """评估单个测试用例"""
        relevant_chunk_ids = set(case["relevant_chunk_ids"])
        ground_truth_answer = case.get("ground_truth", "")
        query = case["question"]

        retrieved_chunk_ids = [r["chunk_id"] for r in retrieved]

        # 计算指标
        hit = int(any(rid in relevant_chunk_ids for rid in retrieved_chunk_ids))
        recalled = len(set(retrieved_chunk_ids) & relevant_chunk_ids)
        recall = recalled / len(relevant_chunk_ids) if relevant_chunk_ids else 0.0
        precision = recalled / top_k

        mrr = 0.0
        for rank, rid in enumerate(retrieved_chunk_ids, 1):
            if rid in relevant_chunk_ids:
                mrr = 1.0 / rank
                break

        return {
            "method": method_name,
            "query_id": case.get("query_id", ""),
            "question": query,
            "ground_truth_answer": ground_truth_answer,
            "relevant_chunk_ids": list(relevant_chunk_ids),
            "retrieved_topk": [
                {
                    "rank": j + 1,
                    "chunk_id": r["chunk_id"],
                    "document_id": r["document_id"],
                    "title": r["title"],
                    "score": round(r.get("score", 0), 4),
                    "source": r.get("source", "vector"),
                    "content": r.get("content", "")[:300] + "..." if len(r.get("content", "")) > 300 else r.get("content", "")
                }
                for j, r in enumerate(retrieved)
            ],
            "metrics": {
                "hit": hit,
                "recall": round(recall, 4),
                "precision": round(precision, 4),
                "mrr": round(mrr, 4),
            }
        }

    # 对每种方法进行评估
    results = {
        "vector": [],
        "bm25": [],
        "hybrid": []
    }

    for i, case in enumerate(chunk_level_cases, 1):
        query = case["question"]

        # 三种检索方式
        vector_retrieved = vector_search(query, top_k)
        bm25_retrieved = bm25_search(query, top_k)
        hybrid_retrieved = hybrid_search(query, top_k)

        # 评估
        results["vector"].append(evaluate_case(case, vector_retrieved, "向量检索"))
        results["bm25"].append(evaluate_case(case, bm25_retrieved, "BM25"))
        results["hybrid"].append(evaluate_case(case, hybrid_retrieved, "混合检索"))

        if i % 10 == 0 or i == len(chunk_level_cases):
            print(f"  - 进度: {i}/{len(chunk_level_cases)}")

    # 6. 汇总结果
    print("\n" + "=" * 80)
    print("评估结果汇总")
    print("=" * 80)

    # 计算每种方法的平均指标
    summary = {}
    for method in ["vector", "bm25", "hybrid"]:
        method_results = results[method]
        summary[method] = {
            f"hit_rate@{top_k}": round(sum(r["metrics"]["hit"] for r in method_results) / len(method_results), 4),
            f"recall@{top_k}": round(sum(r["metrics"]["recall"] for r in method_results) / len(method_results), 4),
            f"precision@{top_k}": round(sum(r["metrics"]["precision"] for r in method_results) / len(method_results), 4),
            "mrr": round(sum(r["metrics"]["mrr"] for r in method_results) / len(method_results), 4),
        }

    # 打印对比表格
    print(f"\n📊 平均指标对比 (Top-{top_k}, Fusion={fusion_method}):")
    print("-" * 80)
    print(f"{'检索方法':<15} {'HitRate@'+str(top_k):<15} {'Recall@'+str(top_k):<15} {'Precision@'+str(top_k):<15} {'MRR':<15}")
    print("-" * 80)

    method_names = {
        "vector": "向量检索(TF-IDF)",
        "bm25": "BM25",
        "hybrid": "混合检索"
    }

    for method in ["vector", "bm25", "hybrid"]:
        m = summary[method]
        print(f"{method_names[method]:<15} {m[f'hit_rate@{top_k}']:<15.4f} {m[f'recall@{top_k}']:<15.4f} {m[f'precision@{top_k}']:<15.4f} {m['mrr']:<15.4f}")

    print("-" * 80)

    # 找出每种方法表现最好的查询
    print("\n📋 详细结果分析:")

    for method in ["vector", "bm25", "hybrid"]:
        print(f"\n{'='*80}")
        print(f"【{method_names[method]}】")
        print(f"{'='*80}")

        method_results = results[method]

        # 按 recall 排序，找出最好和最差的
        sorted_by_recall = sorted(method_results, key=lambda x: x["metrics"]["recall"], reverse=True)

        print(f"\n✅ 表现最好的查询 (Recall@{top_k} = {sorted_by_recall[0]['metrics']['recall']:.4f}):")
        best = sorted_by_recall[0]
        print(f"   Q: {best['question']}")
        print(f"   标准答案: {best['ground_truth_answer'][:80]}...")
        print(f"\n   🔍 Top {top_k} 检索结果:")
        for item in best["retrieved_topk"][:3]:
            match = "✓" if item["chunk_id"] in best["relevant_chunk_ids"] else "✗"
            print(f"      [{item['rank']}] {match} 相似度:{item['score']:.4f} | 来源:{item['source']}")
            print(f"          内容: {item['content'][:100]}...")

        if sorted_by_recall[-1]["metrics"]["recall"] < 1.0:
            print(f"\n❌ 表现最差的查询 (Recall@{top_k} = {sorted_by_recall[-1]['metrics']['recall']:.4f}):")
            worst = sorted_by_recall[-1]
            print(f"   Q: {worst['question']}")
            print(f"   标准答案: {worst['ground_truth_answer'][:80]}...")
            print(f"\n   🔍 Top {top_k} 检索结果:")
            for item in worst["retrieved_topk"][:3]:
                match = "✓" if item["chunk_id"] in worst["relevant_chunk_ids"] else "✗"
                print(f"      [{item['rank']}] {match} 相似度:{item['score']:.4f} | 来源:{item['source']}")
                print(f"          内容: {item['content'][:100]}...")

    # 保存结果
    output_data = {
        "meta": {
            "top_k": top_k,
            "fusion_method": fusion_method,
            "vector_weight": vector_weight,
            "bm25_weight": bm25_weight,
            "rrf_k": rrf_k,
            "ground_truth_path": ground_truth_path,
            "total_cases": len(chunk_level_cases),
        },
        "summary": {
            "vector": summary["vector"],
            "bm25": summary["bm25"],
            "hybrid": summary["hybrid"]
        },
        "detailed_results": results
    }

    output_file = f"backend/tests/recall_comparison_{fusion_method}.json"
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    print(f"\n✅ 结果已保存到: {output_file}")

    return output_data


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="RAG 召回率测试")
    parser.add_argument("--mode", choices=[
        "basic", "chunks", "milvus",
        "gt-memory", "gt-milvus", "compare"
    ], default="basic",
        help="""测试模式:
        basic=使用硬编码测试用例(内存TF-IDF),
        chunks=测试不同chunk size,
        milvus=使用硬编码测试用例(真实Milvus),
        gt-memory=使用Ground Truth数据集(内存TF-IDF),
        gt-milvus=使用Ground Truth数据集(真实Milvus),
        compare=对比三种检索方式(向量/BM25/混合)""")
    parser.add_argument("--top-k", type=int, default=5, help="检索数量")
    parser.add_argument("--collection", default="enterprise_documents", help="Milvus collection名称")
    parser.add_argument("--recreate", action="store_true", help="重建Milvus collection")
    parser.add_argument("--ground-truth", default="tests/ground_truth/ground_truth_auto_dataset.json",
                        help="Ground Truth JSON文件路径")
    parser.add_argument("--fusion", choices=["rrf", "weighted"], default="rrf",
                        help="混合检索融合方法 (rrf=倒数排名融合, weighted=加权融合)")
    parser.add_argument("--vector-weight", type=float, default=0.5,
                        help="向量检索权重 (用于weighted融合)")
    parser.add_argument("--bm25-weight", type=float, default=0.5,
                        help="BM25检索权重 (用于weighted融合)")
    parser.add_argument("--rrf-k", type=int, default=60,
                        help="RRF融合参数k")

    args = parser.parse_args()

    if args.mode == "chunks":
        test_different_chunk_sizes()
    elif args.mode == "milvus":
        run_recall_test_with_milvus(
            collection_name=args.collection,
            recreate=args.recreate
        )
    elif args.mode == "gt-memory":
        run_recall_test_with_ground_truth(
            ground_truth_path=args.ground_truth,
            top_k=args.top_k,
            mode="memory"
        )
    elif args.mode == "gt-milvus":
        run_recall_test_with_ground_truth(
            ground_truth_path=args.ground_truth,
            top_k=args.top_k,
            mode="milvus"
        )
    elif args.mode == "compare":
        compare_retrieval_methods(
            ground_truth_path=args.ground_truth,
            top_k=args.top_k,
            fusion_method=args.fusion,
            vector_weight=args.vector_weight,
            bm25_weight=args.bm25_weight,
            rrf_k=args.rrf_k
        )
    else:
        run_recall_test()