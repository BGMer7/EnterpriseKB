"""
对话相关API
"""
from typing import Optional
from fastapi import APIRouter, Depends, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies import get_current_user, get_rag_pipeline
from app.schemas.chat import ChatRequest, ChatResponse, FeedbackRequest
from app.schemas.admin import ApiResponse
from app.models.user import User

router = APIRouter()


@router.post("/query", response_model=ChatResponse)
async def chat_query(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    rag_pipeline = Depends(get_rag_pipeline)
):
    """
    对话查询
    基于RAG技术回答用户问题
    """
    from app.services.chat_service import chat_service

    return await chat_service.query(
        db=db,
        user=current_user,
        query=request.query,
        conversation_id=request.conversation_id,
        rag_pipeline=rag_pipeline
    )


@router.post("/query/stream")
async def chat_query_stream(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    rag_pipeline = Depends(get_rag_pipeline)
):
    """
    流式对话查询
    返回SSE流式响应
    """
    from app.services.chat_service import chat_service

    return StreamingResponse(
        chat_service.query_stream(
            db=db,
            user=current_user,
            query=request.query,
            conversation_id=request.conversation_id,
            rag_pipeline=rag_pipeline
        ),
        media_type="text/event-stream",
    )


@router.post("/feedback")
async def submit_feedback(
    request: FeedbackRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    提交反馈
    """
    from app.services.chat_service import chat_service

    await chat_service.submit_feedback(
        db=db,
        user_id=str(current_user.id),
        message_id=request.message_id,
        feedback=request.feedback,
        comment=request.comment
    )

    return ApiResponse(message="反馈提交成功")


@router.get("/conversations")
async def list_conversations(
    page: int = 1,
    page_size: int = 20,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    获取对话列表
    """
    from app.services.chat_service import chat_service

    return await chat_service.list_conversations(
        db=db,
        user_id=str(current_user.id),
        page=page,
        page_size=page_size
    )


@router.get("/conversations/{conversation_id}/messages")
async def get_conversation_messages(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    获取对话消息列表
    """
    from app.services.chat_service import chat_service

    return await chat_service.get_conversation_messages(
        db=db,
        conversation_id=conversation_id,
        user=current_user
    )


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    删除对话
    """
    from app.services.chat_service import chat_service

    await chat_service.delete_conversation(
        db=db,
        conversation_id=conversation_id,
        user=current_user
    )

    return ApiResponse(message="对话删除成功")


@router.get("/suggestions")
async def get_suggested_questions():
    """
    获取预设问题
    """
    from app.core.constants import SUGGESTED_QUESTIONS

    return {
        "questions": SUGGESTED_QUESTIONS
    }
