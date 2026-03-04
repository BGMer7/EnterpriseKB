"""
评估数据模型
定义RAG评估所需的数据结构
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class EvaluationSample(BaseModel):
    """单个评估样本"""
    question: str = Field(..., description="用户问题")
    answer: str = Field(..., description="生成的答案")
    contexts: List[str] = Field(..., description="检索到的上下文列表")
    ground_truth: Optional[str] = Field(None, description="参考答案（用于计算Context Recall）")

    class Config:
        from_attributes = True


class EvaluationResult(BaseModel):
    """单次评估结果"""
    question: str = Field(..., description="用户问题")
    # 检索指标
    context_precision: Optional[float] = Field(None, description="Context Precision - 检索内容与问题的相关程度")
    context_recall: Optional[float] = Field(None, description="Context Recall - 检索内容覆盖参考答案的程度")
    # 生成指标
    faithfulness: Optional[float] = Field(None, description="Faithfulness - 答案是否忠实于上下文")
    answer_relevancy: Optional[float] = Field(None, description="Answer Relevancy - 答案与问题的相关程度")
    # 传统指标（基于检索分数）
    avg_retrieval_score: Optional[float] = Field(None, description="平均检索分数")
    retrieval_count: Optional[int] = Field(None, description="检索结果数量")

    class Config:
        from_attributes = True


class EvaluationMetrics(BaseModel):
    """评估指标汇总"""
    total_samples: int = Field(..., description="评估样本数量")
    # 平均指标
    avg_faithfulness: Optional[float] = Field(None, description="平均Faithfulness")
    avg_answer_relevancy: Optional[float] = Field(None, description="平均Answer Relevancy")
    avg_context_precision: Optional[float] = Field(None, description="平均Context Precision")
    avg_context_recall: Optional[float] = Field(None, description="平均Context Recall")
    avg_retrieval_score: Optional[float] = Field(None, description="平均检索分数")
    # 统计信息
    samples_with_context: int = Field(..., description="有检索结果的样本数")
    samples_without_context: int = Field(..., description="无检索结果的样本数")

    class Config:
        from_attributes = True


class EvaluationDataset(BaseModel):
    """评估数据集"""
    samples: List[EvaluationSample] = Field(..., description="评估样本列表")
    name: Optional[str] = Field(None, description="数据集名称")
    description: Optional[str] = Field(None, description="数据集描述")

    class Config:
        from_attributes = True
