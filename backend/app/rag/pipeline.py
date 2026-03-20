"""
RAG Pipeline主流程
整合检索、重排序、LLM生成等模块
支持多provider切换 (custom/langchain/llamaindex/milvus)
"""
import json
from typing import List, Dict, Any, Optional, AsyncGenerator
from pydantic import BaseModel, Field

from .retriever.base import RetrievalResult
from .retriever.hybrid_retriever import HybridRetriever
from .reranker.bge_reranker import get_reranker
from .generator.prompt_builder import PromptBuilder
from .postprocessor.citation import CitationGenerator
from .postprocessor.hallucination_check import HallucinationChecker

from app.integrations.milvus_client import get_milvus_client
from app.integrations.llm_server import get_llm_client
from app.config import settings
from app.core.permissions import get_user_role_names

# 新增：导入 factory
from .retriever.factory import create_retriever
from .providers import RAGProviderType


class RAGResult(BaseModel):
    """RAG Pipeline结果"""
    answer: str = Field(..., description="生成的答案")
    conversation_id: str = Field(..., description="对话ID")
    message_id: str = Field(..., description="消息ID")
    sources: List[Dict[str, Any]] = Field(default_factory=list, description="引用来源")
    suggested_questions: List[str] = Field(default_factory=list, description="建议的后续问题")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")

    class Config:
        from_attributes = True


class RAGPipeline:
    """
    RAG Pipeline
    整合向量检索、BM25检索、重排序、LLM生成等模块
    支持多provider切换
    """

    def __init__(
        self,
        vector_client=None,
        search_client=None,
        llm_client=None,
        reranker=None,
        retriever=None,  # 新增：直接注入retriever
        provider: str = None,  # 新增：选择provider
        top_k: int = settings.RAG_TOP_K,
        reranker_top_k: int = settings.RERANKER_TOP_K,
        min_score: float = settings.RAG_MIN_SCORE,
        max_context_tokens: int = settings.RAG_MAX_CONTEXT_TOKENS
    ):
        self.vector_client = vector_client or get_milvus_client()
        self.search_client = search_client  # Meilisearch
        self.llm_client = llm_client or get_llm_client()
        self.reranker = reranker or get_reranker()

        self.top_k = top_k
        self.reranker_top_k = reranker_top_k
        self.min_score = min_score
        self.max_context_tokens = max_context_tokens
        self.provider = provider  # 记录当前使用的provider

        # 初始化检索器：retriever > provider > default
        if retriever is not None:
            # 直接注入retriever
            self.hybrid_retriever = retriever
        elif provider is not None:
            # 通过provider创建
            self.hybrid_retriever = create_retriever(provider=provider, top_k=top_k * 2)
        else:
            # 默认使用 custom provider (HybridRetriever)
            self.hybrid_retriever = HybridRetriever(
                vector_top_k=top_k * 2,
                bm25_top_k=top_k * 2,
                fusion_k=settings.RAG_FUSION_K
            )

    async def query(
        self,
        query: str,
        user,
        conversation_id: Optional[str] = None,
        stream: bool = False
    ) -> RAGResult:
        """
        执行RAG查询

        Args:
            query: 用户问题
            user: 用户对象
            conversation_id: 对话ID
            stream: 是否流式返回

        Returns:
            RAGResult: 查询结果
        """
        # 1. 检索
        results = await self._retrieve(query, user)

        # 2. 过滤低分结果
        results = [r for r in results if r.score >= self.min_score]

        if not results:
            # 无相关文档，返回拒答
            return RAGResult(
                answer="根据现有文档，未找到相关信息，请咨询相关部门。",
                conversation_id=conversation_id or "",
                message_id=self._generate_id(),
                sources=[],
                suggested_questions=[],
                metadata={"no_relevant_info": True}
            )

        # 3. Rerank
        results = self.reranker.rerank(query, results, self.reranker_top_k)

        # 4. 构建上下文
        context = PromptBuilder.build_context_from_results(
            results,
            self.max_context_tokens
        )

        # 5. 生成答案
        messages = PromptBuilder.build_chat_messages(
            query=query,
            context=context,
            prompt_type="strict"
        )

        answer = await self.llm_client.generate(
            messages=messages,
            temperature=settings.LLM_TEMPERATURE
        )

        # 6. 后处理（引用生成）
        citation_result = CitationGenerator.add_citations_to_answer(
            answer=answer,
            results=results,
            confidence_threshold=0.7
        )

        # 7. 生成建议问题
        suggested_questions = self._generate_suggested_questions(query, results)

        # 8. 构建引用来源
        sources = PromptBuilder.build_citations(results)

        return RAGResult(
            answer=citation_result["answer_with_citations"],
            conversation_id=conversation_id or "",
            message_id=self._generate_id(),
            sources=sources,
            suggested_questions=suggested_questions,
            metadata={
                "retrieval_count": len(results),
                "reranked": True,
                "avg_score": sum(r.score for r in results) / len(results),
            }
        )

    async def query_stream(
        self,
        query: str,
        user,
        conversation_id: Optional[str] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        流式执行RAG查询

        Args:
            query: 用户问题
            user: 用户对象
            conversation_id: 对话ID

        Yields:
            Dict: 流式数据块
        """
        # 1. 发送开始事件
        yield {"type": "start"}

        # 2. 检索
        results = await self._retrieve(query, user)
        results = [r for r in results if r.score >= self.min_score]

        if not results:
            yield {
                "type": "end",
                "content": "根据现有文档，未找到相关信息，请咨询相关部门。",
                "no_relevant_info": True
            }
            return

        # 3. Rerank
        results = self.reranker.rerank(query, results, self.reranker_top_k)

        # 4. 构建上下文
        context = PromptBuilder.build_context_from_results(
            results,
            self.max_context_tokens
        )

        # 5. 发送上下文信息（可选，用于调试）
        # yield {"type": "context", "context": context}

        # 6. 构建消息
        messages = PromptBuilder.build_chat_messages(
            query=query,
            context=context,
            prompt_type="strict"
        )

        # 7. 流式生成答案
        full_answer = ""
        async for chunk in self.llm_client.generate_stream(messages=messages):
            full_answer += chunk
            yield {"type": "chunk", "content": chunk}

        # 8. 后处理
        citation_result = CitationGenerator.add_citations_to_answer(
            answer=full_answer,
            results=results
        )

        sources = PromptBuilder.build_citations(results)
        suggested_questions = self._generate_suggested_questions(query, results)

        # 9. 发送结束事件
        yield {
            "type": "end",
            "content": citation_result["answer_with_citations"],
            "sources": sources,
            "suggested_questions": suggested_questions
        }

    async def _retrieve(
        self,
        query: str,
        user
    ) -> List[RetrievalResult]:
        """
        检索相关文档

        Args:
            query: 查询文本
            user: 用户对象

        Returns:
            List[RetrievalResult]: 检索结果列表
        """
        # 获取用户角色
        user_roles = get_user_role_names(user)
        department_id = str(user.department_id) if user.department_id else None

        # 检查是否为管理员
        from app.core.permissions import is_admin
        if is_admin(user):
            # 管理员无权限限制
            return await self.hybrid_retriever.retrieve(query=query, top_k=self.top_k)

        # 执行带权限的检索
        return await self.hybrid_retriever.retrieve_with_permissions(
            query=query,
            department_id=department_id,
            roles=user_roles,
            top_k=self.top_k
        )

    def _generate_suggested_questions(
        self,
        query: str,
        results: List[RetrievalResult]
    ) -> List[str]:
        """
        生成建议的后续问题

        Args:
            query: 当前问题
            results: 检索结果

        Returns:
            List[str]: 建议问题列表
        """
        # 简单实现：基于文档标题生成
        suggestions = []

        # 提取不同的文档标题
        titles = list(set([r.title for r in results[:3]]))

        # 基于标题生成问题
        for title in titles:
            if "考勤" in title:
                suggestions.append("具体的考勤时间是怎样的？")
            elif "报销" in title:
                suggestions.append("报销流程需要多长时间？")
            elif "请假" in title:
                suggestions.append("年假申请需要提前几天？")
            elif "薪资" in title:
                suggestions.append("薪资发放时间是每月哪天？")

        # 去重并限制数量
        suggestions = list(dict.fromkeys(suggestions))[:3]

        return suggestions

    def _generate_id(self) -> str:
        """生成唯一ID"""
        import uuid
        return str(uuid.uuid4())
