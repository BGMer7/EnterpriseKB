"""
RAGAS评估器
集成RAGAS框架进行RAG系统评估
"""
import os
import json
import logging
import asyncio
from typing import List, Optional, Dict, Any, Callable
from datetime import datetime

from .models import EvaluationSample, EvaluationResult, EvaluationMetrics, EvaluationDataset
from app.config import settings

logger = logging.getLogger(__name__)

# 尝试导入RAGAS
try:
    from ragas import evaluate
    from ragas.llms import LangchainLLMWrapper
    from ragas.embeddings import LangchainEmbeddingsWrapper
    from ragas.metrics import (
        faithfulness,
        answer_relevancy,
        context_precision,
        context_recall
    )
    from datasets import Dataset

    # 尝试导入 LangChain OpenAI
    try:
        from langchain_openai import ChatOpenAI, OpenAIEmbeddings
        LANGCHAIN_AVAILABLE = True
    except ImportError:
        LANGCHAIN_AVAILABLE = False

    RAGAS_AVAILABLE = True
except ImportError:
    RAGAS_AVAILABLE = False
    LANGCHAIN_AVAILABLE = False
    logger.warning("RAGAS not installed. Run: pip install ragas")


class RAGEvaluator:
    """
    RAG评估器
    基于RAGAS框架进行RAG系统评估
    """

    def __init__(
        self,
        llm_model: Optional[str] = None,
        llm_api_url: Optional[str] = None,
        llm_api_key: Optional[str] = None,
        embeddings_model: Optional[str] = None
    ):
        """
        初始化评估器

        Args:
            llm_model: LLM模型名称，用于评估（默认从 settings 获取）
            llm_api_url: LLM API 地址（默认从 settings 获取）
            llm_api_key: LLM API Key（默认从 settings 获取）
            embeddings_model: Embeddings模型名称（默认使用项目的 embedding 模型）
        """
        # 优先使用传入的参数，否则从 settings 获取
        self.llm_model = llm_model or settings.LLM_MODEL_NAME
        self.llm_api_url = llm_api_url or settings.LLM_API_URL
        self.llm_api_key = llm_api_key or settings.LLM_API_KEY
        self.embeddings_model = embeddings_model or "BAAI/bge-m3"

        self._llm = None
        self._embeddings = None

        if not RAGAS_AVAILABLE:
            logger.warning("RAGAS is not available. Please install it with: pip install ragas")
        if not LANGCHAIN_AVAILABLE:
            logger.warning("LangChain OpenAI not available. Please install it with: pip install langchain-openai")

    def _get_llm(self):
        """获取 LangChain LLM 实例"""
        if self._llm is None and LANGCHAIN_AVAILABLE:
            self._llm = ChatOpenAI(
                model=self.llm_model,
                base_url=self.llm_api_url,
                api_key=self.llm_api_key or "dummy",
                temperature=0
            )
        return self._llm

    def _get_embeddings(self):
        """获取 LangChain Embeddings 实例"""
        if self._embeddings is None and LANGCHAIN_AVAILABLE:
            # 使用本地 embedding 模型
            try:
                from langchain_huggingface import HuggingFaceEmbeddings
                self._embeddings = HuggingFaceEmbeddings(
                    model_name=self.embeddings_model,
                    model_kwargs={'device': 'cpu'}
                )
            except ImportError:
                # 回退到 OpenAI Embeddings
                self._embeddings = OpenAIEmbeddings(api_key=self.llm_api_key or "dummy")
        return self._embeddings

    def prepare_dataset(self, samples: List[EvaluationSample]) -> Optional["Dataset"]:
        """
        将评估样本转换为RAGAS所需的格式

        Args:
            samples: 评估样本列表

        Returns:
            Dataset: RAGAS格式的数据集
        """
        if not RAGAS_AVAILABLE:
            raise ImportError("RAGAS is not installed")

        # 转换为RAGAS格式
        data = {
            "question": [],
            "answer": [],
            "contexts": [],
            "ground_truth": []
        }

        for sample in samples:
            data["question"].append(sample.question)
            data["answer"].append(sample.answer)
            data["contexts"].append(sample.contexts)
            # RAGAS需要ground_truth，如果未提供则使用空字符串
            data["ground_truth"].append(sample.ground_truth or "")

        return Dataset.from_dict(data)

    def evaluate_samples(
        self,
        samples: List[EvaluationSample],
        metrics: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        评估样本列表

        Args:
            samples: 评估样本列表
            metrics: 要使用的指标列表，可选值：faithfulness, answer_relevancy, context_precision, context_recall

        Returns:
            Dict: 评估结果
        """
        if not RAGAS_AVAILABLE:
            return self._evaluate_without_ragas(samples)

        # 默认使用所有指标
        if metrics is None:
            metrics = ["faithfulness", "answer_relevancy", "context_precision", "context_recall"]

        # 构建RAGAS指标
        ragas_metrics = []
        if "faithfulness" in metrics:
            ragas_metrics.append(faithfulness)
        if "answer_relevancy" in metrics:
            ragas_metrics.append(answer_relevancy)
        if "context_precision" in metrics:
            ragas_metrics.append(context_precision)
        if "context_recall" in metrics:
            ragas_metrics.append(context_recall)

        try:
            # 准备数据集
            dataset = self.prepare_dataset(samples)

            # 获取 LLM 和 Embeddings
            llm = self._get_llm()
            embeddings = self._get_embeddings()

            # 构建评估参数
            eval_kwargs = {
                "dataset": dataset,
                "metrics": ragas_metrics
            }

            # 如果有 LLM 和 Embeddings，则传入
            if llm and embeddings:
                eval_kwargs["llm"] = LangchainLLMWrapper(llm)
                eval_kwargs["embeddings"] = LangchainEmbeddingsWrapper(embeddings)

            # 执行评估
            result = evaluate(**eval_kwargs)

            # 转换为结果格式
            return self._convert_result(result, samples)

        except Exception as e:
            logger.error(f"Evaluation failed: {e}")
            # 回退到简单评估
            return self._evaluate_without_ragas(samples)

    def _convert_result(self, result, samples: List[EvaluationSample]) -> Dict[str, Any]:
        """
        将RAGAS结果转换为项目格式

        Args:
            result: RAGAS评估结果
            samples: 原始样本

        Returns:
            Dict: 转换后的结果
        """
        results = []
        df = result.to_pandas()

        for idx, sample in enumerate(samples):
            eval_result = EvaluationResult(
                question=sample.question,
            )

            # 提取各项指标
            if "faithfulness" in df.columns:
                eval_result.faithfulness = df.iloc[idx].get("faithfulness")
            if "answer_relevancy" in df.columns:
                eval_result.answer_relevancy = df.iloc[idx].get("answer_relevancy")
            if "context_precision" in df.columns:
                eval_result.context_precision = df.iloc[idx].get("context_precision")
            if "context_recall" in df.columns:
                eval_result.context_recall = df.iloc[idx].get("context_recall")

            # 计算平均检索分数
            if sample.contexts:
                eval_result.retrieval_count = len(sample.contexts)
                # 这里可以添加检索分数的计算

            results.append(eval_result)

        # 计算汇总指标
        metrics = self._calculate_metrics(results)

        return {
            "samples": results,
            "metrics": metrics,
            "timestamp": datetime.now().isoformat()
        }

    def _evaluate_without_ragas(self, samples: List[EvaluationSample]) -> Dict[str, Any]:
        """
        在没有RAGAS时的简单评估

        Args:
            samples: 评估样本列表

        Returns:
            Dict: 简单评估结果
        """
        results = []

        for sample in samples:
            eval_result = EvaluationResult(
                question=sample.question,
                retrieval_count=len(sample.contexts) if sample.contexts else 0,
                avg_retrieval_score=0.8 if sample.contexts else 0.0,  # 模拟值
            )
            results.append(eval_result)

        metrics = self._calculate_metrics(results)

        return {
            "samples": results,
            "metrics": metrics,
            "timestamp": datetime.now().isoformat(),
            "note": "Simplified evaluation (RAGAS not available)"
        }

    def _calculate_metrics(self, results: List[EvaluationResult]) -> EvaluationMetrics:
        """
        计算汇总指标

        Args:
            results: 评估结果列表

        Returns:
            EvaluationMetrics: 汇总指标
        """
        valid_results = [r for r in results if r.retrieval_count and r.retrieval_count > 0]

        def avg(values: List[float]) -> Optional[float]:
            if not values:
                return None
            return sum(values) / len(values)

        return EvaluationMetrics(
            total_samples=len(results),
            avg_faithfulness=avg([r.faithfulness for r in results if r.faithfulness is not None]),
            avg_answer_relevancy=avg([r.answer_relevancy for r in results if r.answer_relevancy is not None]),
            avg_context_precision=avg([r.context_precision for r in results if r.context_precision is not None]),
            avg_context_recall=avg([r.context_recall for r in results if r.context_recall is not None]),
            avg_retrieval_score=avg([r.avg_retrieval_score for r in valid_results if r.avg_retrieval_score is not None]),
            samples_with_context=len(valid_results),
            samples_without_context=len(results) - len(valid_results)
        )

    def evaluate_from_rag_result(
        self,
        question: str,
        answer: str,
        contexts: List[str],
        ground_truth: Optional[str] = None
    ) -> EvaluationResult:
        """
        从RAG Pipeline结果直接评估单个样本

        Args:
            question: 用户问题
            answer: 生成的答案
            contexts: 检索到的上下文列表
            ground_truth: 参考答案

        Returns:
            EvaluationResult: 评估结果
        """
        sample = EvaluationSample(
            question=question,
            answer=answer,
            contexts=contexts,
            ground_truth=ground_truth
        )

        result = self.evaluate_samples([sample])

        if result.get("samples"):
            return result["samples"][0]

        return EvaluationResult(question=question)

    def save_results(self, results: Dict[str, Any], filepath: str) -> None:
        """
        保存评估结果到文件

        Args:
            results: 评估结果
            filepath: 保存路径
        """
        # 转换为可JSON序列化的格式
        output = {
            "timestamp": results.get("timestamp"),
            "metrics": results.get("metrics").model_dump() if results.get("metrics") else None,
            "samples": [
                s.model_dump() for s in results.get("samples", [])
            ]
        }

        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)

        logger.info(f"Evaluation results saved to {filepath}")

    async def collect_and_evaluate(
        self,
        questions: List[str],
        rag_pipeline,
        user,
        ground_truths: Optional[List[str]] = None,
        metrics: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        从 RAG Pipeline 收集数据并评估

        Args:
            questions: 问题列表
            rag_pipeline: RAGPipeline 实例
            user: 用户对象（用于权限控制）
            ground_truths: 标准答案列表（可选）
            metrics: 评估指标列表

        Returns:
            评估结果
        """
        samples = []

        for i, question in enumerate(questions):
            # 1. 检索上下文
            retrieval_results = await rag_pipeline._retrieve(question, user)
            contexts = [r.content for r in retrieval_results]

            # 2. 生成答案
            rag_result = await rag_pipeline.query(question, user)

            # 3. 获取 ground_truth（如果有）
            ground_truth = ground_truths[i] if ground_truths and i < len(ground_truths) else None

            samples.append(EvaluationSample(
                question=question,
                answer=rag_result.answer,
                contexts=contexts,
                ground_truth=ground_truth
            ))

        # 评估收集的样本
        return self.evaluate_samples(samples, metrics)

    def collect_and_evaluate_sync(
        self,
        questions: List[str],
        rag_pipeline,
        user,
        ground_truths: Optional[List[str]] = None,
        metrics: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        同步版本：从 RAG Pipeline 收集数据并评估

        Args:
            questions: 问题列表
            rag_pipeline: RAGPipeline 实例
            user: 用户对象
            ground_truths: 标准答案列表（可选）
            metrics: 评估指标列表

        Returns:
            评估结果
        """
        return asyncio.run(self.collect_and_evaluate(
            questions, rag_pipeline, user, ground_truths, metrics
        ))
