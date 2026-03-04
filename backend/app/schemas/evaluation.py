"""
评估API请求/响应模型
"""
from typing import List, Optional
from pydantic import BaseModel, Field


class EvaluationSampleRequest(BaseModel):
    """评估样本请求"""
    question: str = Field(..., description="用户问题")
    answer: Optional[str] = Field(None, description="生成的答案")
    contexts: List[str] = Field(default_factory=list, description="检索到的上下文列表")
    ground_truth: Optional[str] = Field(None, description="参考答案")


class EvaluationRequest(BaseModel):
    """批量评估请求"""
    samples: List[EvaluationSampleRequest] = Field(..., description="评估样本列表")
    metrics: Optional[List[str]] = Field(
        None,
        description="要使用的指标，可选值：faithfulness, answer_relevancy, context_precision, context_recall"
    )


class EvaluationSampleResponse(BaseModel):
    """评估样本响应"""
    question: str
    faithfulness: Optional[float] = None
    answer_relevancy: Optional[float] = None
    context_precision: Optional[float] = None
    context_recall: Optional[float] = None
    retrieval_count: Optional[int] = None
    avg_retrieval_score: Optional[float] = None


class EvaluationMetricsResponse(BaseModel):
    """评估指标汇总响应"""
    total_samples: int
    avg_faithfulness: Optional[float] = None
    avg_answer_relevancy: Optional[float] = None
    avg_context_precision: Optional[float] = None
    avg_context_recall: Optional[float] = None
    avg_retrieval_score: Optional[float] = None
    samples_with_context: int
    samples_without_context: int


class EvaluationResponse(BaseModel):
    """评估响应"""
    metrics: EvaluationMetricsResponse
    samples: List[EvaluationSampleResponse]
    timestamp: str
    note: Optional[str] = None
