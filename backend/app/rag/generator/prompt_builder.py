"""
Prompt构建器
构建RAG系统的提示词
"""
from typing import List, Dict, Any, Optional
from .base import RetrievalResult


class PromptBuilder:
    """
    Prompt构建器
    """

    @staticmethod
    def build_system_prompt(
        context: str,
        prompt_type: str = "default"
    ) -> str:
        """
        构建系统提示词

        Args:
            context: 检索到的上下文
            prompt_type: Prompt类型 (default, strict, concise)

        Returns:
            str: 系统提示词
        """
        prompts = {
            "default": """你是一个企业制度查询助手。请基于以下检索到的文档内容回答用户问题。

【检索到的文档】
{context}

【重要说明】
1. 你的回答必须**完全基于**以上提供的文档内容
2. 不要编造任何文档中没有的信息
3. 如果文档内容不足以回答问题，请如实说明
4. 引用具体条款时，请标注文档标题和章节
5. 回答要简洁、准确、专业

【用户问题】
{{query}}

【请回答】""",

            "strict": """你是一个企业制度查询助手。请基于以下检索到的文档内容回答用户问题。

【检索到的文档】
{context}

【严格约束】
1. 必须**仅基于**提供的文档内容回答
2. 不得添加任何文档中未提及的信息
3. 如果文档中没有相关信息，请明确回答"根据现有文档，未找到相关信息"
4. 对于制度类问题，引用原文条款时请标注来源
5. 保持客观中立，不进行主观推测
6. 答案格式：
   - 先给出简洁答案（1-2句话）
   - 如有需要，提供详细说明
   - 引用的文档格式：[文档标题 - 章节]

【用户问题】
{{query}}

【请回答】""",

            "concise": """你是一个企业制度查询助手。请基于以下检索到的文档内容简洁回答用户问题。

【检索到的文档】
{context}

【约束】
1. 基于文档内容直接回答
2. 回答简洁明了，不超过200字
3. 如无相关信息，请说明

【用户问题】
{{query}}

【请回答】""",
        }

        return prompts.get(prompt_type, prompts["default"])

    @staticmethod
    def build_chat_messages(
        query: str,
        context: str,
        history: Optional[List[Dict[str, str]]] = None,
        prompt_type: str = "default"
    ) -> List[Dict[str, str]]:
        """
        构建对话消息列表

        Args:
            query: 用户问题
            context: 检索到的上下文
            history: 对话历史
            prompt_type: Prompt类型

        Returns:
            List[Dict]: 消息列表
        """
        messages = []

        # 系统提示
        messages.append({
            "role": "system",
            "content": PromptBuilder.build_system_prompt(context, prompt_type)
        })

        # 历史对话
        if history:
            messages.extend(history)

        # 当前问题
        messages.append({
            "role": "user",
            "content": query
        })

        return messages

    @staticmethod
    def build_context_from_results(
        results: List[RetrievalResult],
        max_tokens: int = 4000
    ) -> str:
        """
        从检索结果构建上下文字符串

        Args:
            results: 检索结果列表
            max_tokens: 最大token数限制

        Returns:
            str: 格式化的上下文字符串
        """
        if not results:
            return "未找到相关文档。"

        context_parts = []
        current_tokens = 0

        for idx, result in enumerate(results, 1):
            # 估算token数（粗略估算：1汉字≈1.5token）
            chunk_tokens = len(result.content) * 1.5

            if current_tokens + chunk_tokens > max_tokens:
                break

            context_parts.append(
                f"【文档{idx}】{result.title}\n"
                f"来源：{result.section or 'N/A'}\n"
                f"页码：{result.page_number or 'N/A'}\n"
                f"内容：{result.content}"
            )

            current_tokens += chunk_tokens

        return "\n\n".join(context_parts)

    @staticmethod
    def build_citations(
        results: List[RetrievalResult]
    ) -> List[Dict[str, Any]]:
        """
        构建引用信息

        Args:
            results: 检索结果列表

        Returns:
            List[Dict]: 引用信息列表
        """
        citations = []

        for result in results:
            citations.append({
                "chunk_id": result.chunk_id,
                "document_id": result.document_id,
                "document_title": result.title,
                "section": result.section,
                "page_number": result.page_number,
                "content_preview": result.content[:200] + "..." if len(result.content) > 200 else result.content,
                "score": result.score,
            })

        return citations
