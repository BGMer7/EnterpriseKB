"""
RAG评估API
提供RAG系统评估接口
"""
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.evaluation import (
    EvaluationRequest,
    EvaluationResponse,
    EvaluationSampleRequest
)

router = APIRouter()


def _get_evaluator_and_sample():
    """延迟导入评估器，避免循环依赖"""
    from app.rag.evaluation import RAGEvaluator
    from app.rag.evaluation.models import EvaluationSample
    return RAGEvaluator, EvaluationSample


@router.post("/evaluate", response_model=EvaluationResponse)
async def evaluate_rag(
    request: EvaluationRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    评估RAG系统

    使用RAGAS框架评估RAG系统的质量，包括：
    - Faithfulness: 答案是否忠实于检索到的上下文
    - Answer Relevancy: 答案与问题的相关程度
    - Context Precision: 检索内容与问题的相关程度
    - Context Recall: 检索内容覆盖参考答案的程度
    """
    # 延迟导入
    RAGEvaluator, EvaluationSample = _get_evaluator_and_sample()

    # 转换请求数据为评估样本
    samples = [
        EvaluationSample(
            question=s.question,
            answer=s.answer or "",
            contexts=s.contexts,
            ground_truth=s.ground_truth
        )
        for s in request.samples
    ]

    # 执行评估
    evaluator = RAGEvaluator()
    results = evaluator.evaluate_samples(samples, metrics=request.metrics)

    # 构建响应
    metrics_data = results["metrics"]
    return EvaluationResponse(
        metrics={
            "total_samples": metrics_data.total_samples,
            "avg_faithfulness": metrics_data.avg_faithfulness,
            "avg_answer_relevancy": metrics_data.avg_answer_relevancy,
            "avg_context_precision": metrics_data.avg_context_precision,
            "avg_context_recall": metrics_data.avg_context_recall,
            "avg_retrieval_score": metrics_data.avg_retrieval_score,
            "samples_with_context": metrics_data.samples_with_context,
            "samples_without_context": metrics_data.samples_without_context
        },
        samples=[
            EvaluationSampleResponse(
                question=s.question,
                faithfulness=s.faithfulness,
                answer_relevancy=s.answer_relevancy,
                context_precision=s.context_precision,
                context_recall=s.context_recall,
                retrieval_count=s.retrieval_count,
                avg_retrieval_score=s.avg_retrieval_score
            )
            for s in results["samples"]
        ],
        timestamp=results["timestamp"],
        note=results.get("note")
    )


@router.post("/evaluate/single")
async def evaluate_single(
    sample: EvaluationSampleRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    评估单个查询

    对单个问答进行快速评估
    """
    # 延迟导入
    RAGEvaluator, _ = _get_evaluator_and_sample()

    evaluator = RAGEvaluator()

    result = evaluator.evaluate_from_rag_result(
        question=sample.question,
        answer=sample.answer or "",
        contexts=sample.contexts,
        ground_truth=sample.ground_truth
    )

    return {
        "question": result.question,
        "faithfulness": result.faithfulness,
        "answer_relevancy": result.answer_relevancy,
        "context_precision": result.context_precision,
        "context_recall": result.context_recall,
        "retrieval_count": result.retrieval_count,
        "avg_retrieval_score": result.avg_retrieval_score
    }
