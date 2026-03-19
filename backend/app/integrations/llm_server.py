"""
LLM客户端
支持 vLLM (本地) 和 MiniMax (云端)
"""
import json
from typing import Optional, List, Dict, Any, AsyncGenerator
from contextlib import asynccontextmanager

import httpx
from openai import AsyncOpenAI

from app.config import settings


class LLMClient:
    """
    LLM客户端（支持 vLLM 和 MiniMax）
    """

    def __init__(
        self,
        provider: str = None,
        api_url: str = settings.LLM_API_URL,
        api_key: str = settings.LLM_API_KEY,
        model_name: str = settings.LLM_MODEL_NAME,
        max_tokens: int = settings.LLM_MAX_TOKENS,
        temperature: float = settings.LLM_TEMPERATURE,
        timeout: int = settings.LLM_TIMEOUT
    ):
        self.provider = provider or settings.LLM_PROVIDER
        self.api_url = api_url
        self.api_key = api_key
        self.model_name = model_name
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.timeout = timeout
        self._client = None

    def connect(self) -> AsyncOpenAI:
        """
        连接到LLM服务器
        """
        if self._client is None:
            # MiniMax 使用不同的 API 端点
            if self.provider == "minimax":
                base_url = "https://api.minimax.chat/v1"
            else:
                base_url = self.api_url

            self._client = AsyncOpenAI(
                base_url=base_url,
                api_key=self.api_key or "dummy",
                timeout=self.timeout
            )
        return self._client

    @property
    def client(self) -> AsyncOpenAI:
        """获取OpenAI客户端"""
        if self._client is None:
            self.connect()
        return self._client

    async def check_health(self) -> str:
        """
        检查LLM服务健康状态
        """
        try:
            # 尝试发送一个简单的测试请求来检查连接
            test_messages = [
                {"role": "user", "content": "hi"}
            ]
            await self.client.chat.completions.create(
                model=self.model_name,
                messages=test_messages,
                max_tokens=10
            )
            return "healthy"
        except Exception as e:
            error_msg = str(e)
            if "401" in error_msg or "authorized" in error_msg.lower():
                return f"unhealthy: API认证失败，请检查 API Key"
            elif "404" in error_msg:
                return f"unhealthy: API端点不存在"
            elif "connection" in error_msg.lower():
                return f"unhealthy: 连接失败"
            else:
                return f"unhealthy: {error_msg[:50]}"

    # ===== 生成方法 =====
    async def generate(
        self,
        messages: List[Dict[str, str]],
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        stop: Optional[List[str]] = None,
        stream: bool = False
    ) -> str:
        """
        生成回复（非流式）

        Args:
            messages: 对话消息列表
            max_tokens: 最大生成token数
            temperature: 温度参数
            stop: 停止词列表
            stream: 是否流式输出

        Returns:
            str: 生成的回复
        """
        client = self.client

        try:
            response = await client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                max_tokens=max_tokens or self.max_tokens,
                temperature=temperature if temperature is not None else self.temperature,
                stop=stop,
                stream=stream
            )

            return response.choices[0].message.content

        except Exception as e:
            raise RuntimeError(f"LLM generation failed: {str(e)}")

    async def generate_stream(
        self,
        messages: List[Dict[str, str]],
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        stop: Optional[List[str]] = None
    ) -> AsyncGenerator[str, None]:
        """
        流式生成回复

        Args:
            messages: 对话消息列表
            max_tokens: 最大生成token数
            temperature: 温度参数
            stop: 停止词列表

        Yields:
            str: 生成的文本片段
        """
        client = self.client

        try:
            stream = await client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                max_tokens=max_tokens or self.max_tokens,
                temperature=temperature if temperature is not None else self.temperature,
                stop=stop,
                stream=True
            )

            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        except Exception as e:
            raise RuntimeError(f"LLM streaming failed: {str(e)}")

    # ===== SSE流式响应 =====
    async def generate_sse(
        self,
        messages: List[Dict[str, str]],
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        stop: Optional[List[str]] = None
    ) -> AsyncGenerator[str, None]:
        """
        生成SSE格式的流式响应

        Args:
            messages: 对话消息列表
            max_tokens: 最大生成token数
            temperature: 温度参数
            stop: 停止词列表

        Yields:
            str: SSE格式的数据块
        """
        try:
            # 发送开始事件
            yield "event: start\ndata: {\"type\": \"start\"}\n\n"

            full_content = ""

            # 流式生成
            async for chunk in self.generate_stream(
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                stop=stop
            ):
                full_content += chunk
                # 发送数据块
                data = json.dumps({
                    "type": "chunk",
                    "content": chunk
                }, ensure_ascii=False)
                yield f"event: message\ndata: {data}\n\n"

            # 发送结束事件
            end_data = json.dumps({
                "type": "end",
                "content": full_content
            }, ensure_ascii=False)
            yield f"event: end\ndata: {end_data}\n\n"

        except Exception as e:
            # 发送错误事件
            error_data = json.dumps({
                "type": "error",
                "error": str(e)
            }, ensure_ascii=False)
            yield f"event: error\ndata: {error_data}\n\n"

    # ===== Prompt构建辅助 =====
    def build_messages(
        self,
        system_prompt: str,
        user_query: str,
        context: str,
        history: Optional[List[Dict[str, str]]] = None
    ) -> List[Dict[str, str]]:
        """
        构建对话消息列表

        Args:
            system_prompt: 系统提示词
            user_query: 用户问题
            context: 检索到的上下文
            history: 对话历史

        Returns:
            List[Dict]: 消息列表
        """
        messages = []

        # 系统提示
        messages.append({
            "role": "system",
            "content": system_prompt.format(context=context)
        })

        # 历史对话
        if history:
            messages.extend(history)

        # 当前问题
        messages.append({
            "role": "user",
            "content": user_query
        })

        return messages

    # ===== 默认Prompt模板 =====
    @staticmethod
    def get_default_system_prompt() -> str:
        """
        获取默认系统提示词
        """
        return """你是一个企业制度查询助手。请基于以下检索到的文档内容回答用户问题。

【重要约束】
1. 必须**仅基于**提供的文档内容回答，不得添加文档中未提及的信息
2. 如果文档中没有相关信息，请明确回答"根据现有文档，未找到相关信息"
3. 对于制度类问题，引用原文条款时请标注来源
4. 保持客观中立，不进行主观推测
5. 答案格式：
   - 先给出简洁答案（1-2句话）
   - 如有需要，提供详细说明
   - 引用的文档格式：[文档标题 - 章节]

【检索到的文档】
{context}

【用户问题】
{{query}}

【请回答】"""

    @staticmethod
    def get_rag_system_prompt() -> str:
        """
        获取RAG专用系统提示词
        """
        return """你是一个企业制度查询助手。请基于以下检索到的文档内容回答用户问题。

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

【请回答】"""


# 全局LLM客户端实例
llm_client = LLMClient()


def get_llm_client() -> LLMClient:
    """获取LLM客户端单例"""
    return llm_client
