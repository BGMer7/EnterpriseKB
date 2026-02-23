"""
Retriever基类定义
"""
from typing import List, Optional, Any
from pydantic import BaseModel, Field


class RetrievalResult(BaseModel):
    """检索结果"""
    id: str = Field(..., description="结果ID")
    chunk_id: str = Field(..., description="Chunk ID")
    document_id: str = Field(..., description="Document ID")
    content: str = Field(..., description="Chunk内容")
    title: str = Field(..., description="文档标题")
    score: float = Field(..., description="相关性分数")
    metadata: dict = Field(default_factory=dict, description="元数据")
    department_id: Optional[str] = Field(None, description="部门ID")
    is_public: Optional[bool] = Field(None, description="是否公开")
    allowed_roles: List[str] = Field(default_factory=list, description="允许的角色列表")
    page_number: Optional[int] = Field(None, description="页码")
    section: Optional[str] = Field(None, description="章节")
    chunk_index: Optional[int] = Field(None, description="Chunk索引")

    class Config:
        from_attributes = True


class BaseRetriever:
    """
    Retriever基类
    """

    async def retrieve(
        self,
        query: str,
        top_k: int = 30,
        filter_expression: Optional[str] = None
    ) -> List[RetrievalResult]:
        """
        检索相关文档

        Args:
            query: 查询文本
            top_k: 返回结果数量
            filter_expression: 过滤表达式

        Returns:
            List[RetrievalResult]: 检索结果列表
        """
        raise NotImplementedError

    async def retrieve_with_context(
        self,
        query: str,
        top_k: int = 30,
        filter_expression: Optional[str] = None
    ) -> tuple[List[RetrievalResult], str]:
        """
        检索并返回格式化的上下文字符串

        Args:
            query: 查询文本
            top_k: 返回结果数量
            filter_expression: 过滤表达式

        Returns:
            tuple: (检索结果列表, 格式化的上下文字符串)
        """
        results = await self.retrieve(query, top_k, filter_expression)

        # 格式化上下文
        context_parts = []
        for idx, result in enumerate(results, 1):
            context_parts.append(
                f"【文档{idx}】{result.title}\n"
                f"来源：{result.section or 'N/A'}\n"
                f"页码：{result.page_number or 'N/A'}\n"
                f"内容：{result.content}"
            )

        context = "\n\n".join(context_parts)

        return results, context

    def normalize_scores(self, results: List[RetrievalResult]) -> List[RetrievalResult]:
        """
        归一化分数到[0, 1]范围

        Args:
            results: 检索结果列表

        Returns:
            List[RetrievalResult]: 分数归一化后的结果列表
        """
        if not results:
            return results

        # 获取所有分数
        scores = [r.score for r in results]
        min_score = min(scores)
        max_score = max(scores)

        if max_score == min_score:
            # 所有分数相同，返回0.5
            for r in results:
                r.score = 0.5
        else:
            # 归一化到[0, 1]
            for r in results:
                r.score = (r.score - min_score) / (max_score - min_score)

        return results
