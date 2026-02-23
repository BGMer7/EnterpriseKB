"""
对话服务
实现对话管理、消息处理、RAG调用
"""
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.db.session import get_db_session
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.audit_log import AuditLog
from app.models.user import User
from app.rag.pipeline import RAGPipeline, RAGResult
from app.core.constants import MessageRole, FeedbackType
from app.schemas.chat import ChatResponse, SourceReference
from app.integrations.milvus_client import get_milvus_client
from app.integrations.search_engine import get_meilisearch_client
from app.integrations.llm_server import get_llm_client
from app.config import settings

logger = logging.getLogger(__name__)


class ChatService:
    """对话服务"""

    def __init__(self):
        self._rag_pipeline: Optional[RAGPipeline] = None

    def get_rag_pipeline(self) -> RAGPipeline:
        """获取RAG Pipeline实例（懒加载）"""
        if self._rag_pipeline is None:
            self._rag_pipeline = RAGPipeline(
                vector_client=get_milvus_client(),
                search_client=get_meilisearch_client(),
                llm_client=get_llm_client()
            )
        return self._rag_pipeline

    async def query(
        self,
        db: AsyncSession,
        user: User,
        query: str,
        conversation_id: Optional[str] = None,
        rag_pipeline: Optional[RAGPipeline] = None
    ) -> ChatResponse:
        """
        对话查询

        Args:
            db: 数据库会话
            user: 用户对象
            query: 用户问题
            conversation_id: 对话ID
            rag_pipeline: RAG Pipeline实例

        Returns:
            ChatResponse: 对话响应
        """
        # 1. 获取或创建对话
        if not conversation_id:
            conversation = Conversation(
                user_id=str(user.id),
                title=self._generate_title(query)
            )
            db.add(conversation)
            await db.commit()
            await db.refresh(conversation)
        else:
            result = await db.execute(
                select(Conversation).where(Conversation.id == conversation_id)
            )
            conversation = result.scalar_one_or_none()

        if not conversation:
            raise ValueError(f"Conversation {conversation_id} not found")

        # 2. 获取对话历史（用于上下文）
        history = await self._get_conversation_history(db, conversation.id)

        # 3. 调用RAG Pipeline
        pipeline = rag_pipeline or self.get_rag_pipeline()
        rag_result = await pipeline.query(
            query=query,
            user=user,
            conversation_id=str(conversation.id),
            stream=False
        )

        # 4. 保存用户消息
        user_message = Message(
            conversation_id=str(conversation.id),
            role=MessageRole.USER,
            content=query
        )
        db.add(user_message)
        await db.commit()

        # 5. 保存助手消息
        assistant_message = Message(
            conversation_id=str(conversation.id),
            role=MessageRole.ASSISTANT,
            content=rag_result.answer,
            sources=rag_result.sources
        )
        db.add(assistant_message)
        await db.commit()

        # 6. 更新对话时间
        conversation.updated_at = datetime.utcnow()
        if not conversation.title:
            conversation.title = self._generate_title(query)
        await db.commit()

        # 7. 记录审计日志
        await self._log_audit(db, user, "query", {
            "query": query,
            "conversation_id": str(conversation.id),
            "sources_count": len(rag_result.sources),
            "has_answer": not rag_result.metadata.get("no_relevant_info", False)
        })

        return ChatResponse(
            conversation_id=str(conversation.id),
            message_id=str(assistant_message.id),
            answer=rag_result.answer,
            sources=rag_result.sources,
            suggested_questions=rag_result.suggested_questions
        )

    async def query_stream(
        self,
        db: AsyncSession,
        user: User,
        query: str,
        conversation_id: Optional[str] = None,
        rag_pipeline: Optional[RAGPipeline] = None
    ):
        """
        流式对话查询

        Args:
            db: 数据库会话
            user: 用户对象
            query: 用户问题
            conversation_id: 对话ID
            rag_pipeline: RAG Pipeline实例

        Yields:
            str: SSE格式的数据
        """
        # 1. 获取或创建对话
        if not conversation_id:
            conversation = Conversation(
                user_id=str(user.id),
                title=self._generate_title(query)
            )
            db.add(conversation)
            await db.commit()
            await db.refresh(conversation)
        else:
            result = await db.execute(
                select(Conversation).where(Conversation.id == conversation_id)
            )
            conversation = result.scalar_one_or_none()

        if not conversation:
            raise ValueError(f"Conversation {conversation_id} not found")

        # 2. 保存用户消息
        user_message = Message(
            conversation_id=str(conversation.id),
            role=MessageRole.USER,
            content=query
        )
        db.add(user_message)
        await db.commit()
        await db.refresh(user_message)

        # 3. 调用RAG Pipeline（流式）
        pipeline = rag_pipeline or self.get_rag_pipeline()

        full_answer = ""
        user_message_id = str(user_message.id)

        async for chunk in pipeline.query_stream(
            query=query,
            user=user,
            conversation_id=str(conversation.id)
        ):
            if chunk.get("type") == "start":
                yield f"event: start\ndata: {{\"type\": \"start\", \"message_id\": \"{user_message_id}\"}}\n\n"

            elif chunk.get("type") == "chunk":
                content = chunk.get("content", "")
                full_answer += content
                data = {
                    "type": "chunk",
                    "message_id": user_message_id,
                    "content": content
                }
                yield f"event: message\ndata: {self._to_json(data)}\n\n"

            elif chunk.get("type") == "end":
                full_answer = chunk.get("content", full_answer)

                # 保存助手消息
                assistant_message = Message(
                    conversation_id=str(conversation.id),
                    role=MessageRole.ASSISTANT,
                    content=full_answer,
                    sources=chunk.get("sources", [])
                )
                db.add(assistant_message)
                await db.commit()

                # 更新对话
                conversation.updated_at = datetime.utcnow()
                await db.commit()

                end_data = {
                    "type": "end",
                    "message_id": str(assistant_message.id),
                    "content": full_answer,
                    "sources": chunk.get("sources", []),
                    "suggested_questions": chunk.get("suggested_questions", [])
                }
                yield f"event: end\ndata: {self._to_json(end_data)}\n\n"

            elif chunk.get("type") == "error":
                error_data = {
                    "type": "error",
                    "message_id": user_message_id,
                    "error": chunk.get("error", "Unknown error")
                }
                yield f"event: error\ndata: {self._to_json(error_data)}\n\n"

    async def list_conversations(
        self,
        db: AsyncSession,
        user_id: str,
        page: int = 1,
        page_size: int = 20
    ) -> Dict[str, Any]:
        """
        获取对话列表

        Args:
            db: 数据库会话
            user_id: 用户ID
            page: 页码
            page_size: 每页数量

        Returns:
            Dict: 对话列表
        """
        query = select(Conversation).where(Conversation.user_id == user_id)
        query = query.order_by(Conversation.updated_at.desc())

        # 分页
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await db.execute(query)
        conversations = result.scalars().all()

        # 计算每个对话的消息数
        conv_ids = [c.id for c in conversations]
        message_counts = {}
        if conv_ids:
            count_result = await db.execute(
                select(Message.conversation_id, func.count(Message.id))
                .where(Message.conversation_id.in_(conv_ids))
                .group_by(Message.conversation_id)
            )
            for conv_id, count in count_result:
                message_counts[conv_id] = count

        # 添加消息数到结果
        conversations_data = []
        for conv in conversations:
            conversations_data.append({
                "id": str(conv.id),
                "title": conv.title or "新对话",
                "created_at": conv.created_at,
                "updated_at": conv.updated_at,
                "message_count": message_counts.get(str(conv.id), 0)
            })

        # 计算总数
        count_query = select(func.count()).select_from(query.subquery().limit(None))
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        return {
            "conversations": conversations_data,
            "total": total,
            "page": page,
            "page_size": page_size
        }

    async def get_conversation_messages(
        self,
        db: AsyncSession,
        conversation_id: str,
        user: User
    ) -> List[Message]:
        """
        获取对话消息列表

        Args:
            db: 数据库会话
            conversation_id: 对话ID
            user: 用户对象

        Returns:
            List[Message]: 消息列表
        """
        # 权限检查
        result = await db.execute(
            select(Conversation).where(Conversation.id == conversation_id)
        )
        conversation = result.scalar_one_or_none()

        if not conversation:
            raise ValueError(f"Conversation {conversation_id} not found")

        if conversation.user_id != str(user.id):
            raise PermissionError("You don't have permission to view this conversation")

        # 获取消息
        result = await db.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at)
        )
        messages = result.scalars().all()

        return messages

    async def delete_conversation(
        self,
        db: AsyncSession,
        conversation_id: str,
        user: User
    ):
        """
        删除对话

        Args:
            db: 数据库会话
            conversation_id: 对话ID
            user: 用户对象
        """
        # 权限检查
        result = await db.execute(
            select(Conversation).where(Conversation.id == conversation_id)
        )
        conversation = result.scalar_one_or_none()

        if not conversation:
            raise ValueError(f"Conversation {conversation_id} not found")

        if conversation.user_id != str(user.id):
            raise PermissionError("You don't have permission to delete this conversation")

        # 删除消息（级联）
        await db.delete(conversation)
        await db.commit()

        logger.info(f"Conversation {conversation_id} deleted by {user.name}")

    async def submit_feedback(
        self,
        db: AsyncSession,
        user_id: str,
        message_id: str,
        feedback: str,
        comment: Optional[str] = None
    ):
        """
        提交反馈

        Args:
            db: 数据库会话
            user_id: 用户ID
            message_id: 消息ID
            feedback: 反馈类型
            comment: 评论内容
        """
        result = await db.execute(
            select(Message).where(Message.id == message_id)
        )
        message = result.scalar_one_or_none()

        if not message:
            raise ValueError(f"Message {message_id} not found")

        # 验证反馈类型
        if feedback not in [FeedbackType.HELPFUL, FeedbackType.NOT_HELPFUL, FeedbackType.INACCURATE]:
            raise ValueError(f"Invalid feedback type: {feedback}")

        message.feedback = feedback
        message.feedback_comment = comment
        await db.commit()

        logger.info(f"Feedback submitted for message {message_id}: {feedback}")

    def _generate_title(self, query: str) -> str:
        """
        生成对话标题

        Args:
            query: 用户问题

        Returns:
            str: 标题
        """
        # 截取标题（最多20个字符）
        return query[:20] if len(query) > 20 else query

    async def _get_conversation_history(
        self,
        db: AsyncSession,
        conversation_id: str
    ) -> List[Dict[str, str]]:
        """
        获取对话历史

        Args:
            db: 数据库会话
            conversation_id: 对话ID

        Returns:
            List[Dict]: 消息历史列表
        """
        result = await db.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at)
        )
        messages = result.scalars().all()

        # 转换为LLM消息格式
        history = []
        for msg in messages:
            if msg.role in [MessageRole.USER, MessageRole.ASSISTANT]:
                history.append({
                    "role": msg.role,
                    "content": msg.content
                })

        return history

    async def _log_audit(
        self,
        db: AsyncSession,
        user: User,
        action: str,
        request_data: Optional[Dict] = None
    ):
        """
        记录审计日志

        Args:
            db: 数据库会话
            user: 用户对象
            action: 操作类型
            request_data: 请求数据
        """
        audit_log = AuditLog(
            user_id=str(user.id),
            action=action,
            request_data=request_data or {}
        )

        db.add(audit_log)
        try:
            await db.commit()
        except Exception as e:
            logger.error(f"Failed to log audit: {e}")

    @staticmethod
    def _to_json(data: dict) -> str:
        """转换为JSON字符串"""
        import json
        return json.dumps(data, ensure_ascii=False)


# 全局对话服务实例
chat_service = ChatService()


def get_chat_service() -> ChatService:
    """获取对话服务单例"""
    return chat_service
