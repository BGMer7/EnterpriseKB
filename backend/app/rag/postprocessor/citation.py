"""
引用生成器
为LLM回答添加引用标注
"""
import re
from typing import List, Dict, Any, Optional
from ..retriever.base import RetrievalResult


class CitationGenerator:
    """
    引用生成器
    """

    @staticmethod
    def add_citations_to_answer(
        answer: str,
        results: List[RetrievalResult],
        confidence_threshold: float = 0.8
    ) -> Dict[str, Any]:
        """
        为答案添加引用标注

        Args:
            answer: LLM生成的答案
            results: 检索结果列表
            confidence_threshold: 引用置信度阈值

        Returns:
            Dict: {
                "answer_with_citations": str,  # 带引用的答案
                "citations": List[Dict],       # 引用列表
            }
        """
        citations = []

        # 简单实现：为每个结果添加引用
        for idx, result in enumerate(results):
            if result.score >= confidence_threshold:
                citations.append({
                    "index": idx + 1,
                    "chunk_id": result.chunk_id,
                    "document_id": result.document_id,
                    "document_title": result.title,
                    "section": result.section,
                    "page_number": result.page_number,
                    "content_preview": result.content[:100] + "..." if len(result.content) > 100 else result.content,
                    "score": result.score,
                })

        # 在答案末尾添加引用列表
        if citations:
            citation_text = "\n\n【参考来源】\n"
            for citation in citations:
                citation_text += f"{citation['index']}. {citation['document_title']}"
                if citation["section"]:
                    citation_text += f" - {citation['section']}"
                citation_text += "\n"

            answer_with_citations = answer + citation_text
        else:
            answer_with_citations = answer

        return {
            "answer_with_citations": answer_with_citations,
            "citations": citations
        }

    @staticmethod
    def find_relevant_citations(
        answer: str,
        results: List[RetrievalResult]
    ) -> List[Dict[str, Any]]:
        """
        在答案中查找相关的引用并添加标注

        Args:
            answer: LLM生成的答案
            results: 检索结果列表

        Returns:
            List[Dict]: 引用列表
        """
        citations = []

        for idx, result in enumerate(results):
            # 检查答案中是否包含文档标题的部分内容
            if result.title and result.title in answer:
                citations.append({
                    "index": idx + 1,
                    "chunk_id": result.chunk_id,
                    "document_id": result.document_id,
                    "document_title": result.title,
                    "section": result.section,
                    "page_number": result.page_number,
                })

        return citations

    @staticmethod
    def extract_key_phrases(text: str) -> List[str]:
        """
        提取文本中的关键短语

        Args:
            text: 输入文本

        Returns:
            List[str]: 关键短语列表
        """
        # 简单实现：提取名词短语
        # TODO: 使用NLP库进行更精确的提取
        phrases = []

        # 提取引号内容
        quoted_phrases = re.findall(r'"([^"]+)"', text)
        phrases.extend(quoted_phrases)

        # 提取书名号内容
        book_phrases = re.findall(r'《([^》]+)》', text)
        phrases.extend(book_phrases)

        return phrases
