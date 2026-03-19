"""
对话相关API（简化版，不依赖数据库）
"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from app.dependencies import get_current_user, get_rag_pipeline
from app.schemas.chat import ChatRequest, ChatResponse, FeedbackRequest
from app.schemas.admin import ApiResponse

router = APIRouter()


@router.post("/query", response_model=ChatResponse)
async def chat_query(
    request: ChatRequest,
    current_user = Depends(get_current_user),
    rag_pipeline = Depends(get_rag_pipeline)
):
    """
    对话查询（简化版）
    基于RAG技术回答用户问题
    """
    result = await rag_pipeline.query(
        query=request.query,
        user=current_user,
        conversation_id=request.conversation_id
    )

    return {
        "answer": result.answer,
        "conversation_id": result.conversation_id,
        "message_id": result.message_id,
        "sources": result.sources,
        "suggested_questions": result.suggested_questions
    }


@router.post("/query/stream")
async def chat_query_stream(
    request: ChatRequest,
    current_user = Depends(get_current_user),
    rag_pipeline = Depends(get_rag_pipeline)
):
    """
    流式对话查询
    返回SSE流式响应
    """
    return StreamingResponse(
        rag_pipeline.query_stream(
            query=request.query,
            user=current_user,
            conversation_id=request.conversation_id
        ),
        media_type="text/event-stream",
    )


@router.post("/feedback")
async def submit_feedback(request: FeedbackRequest):
    """提交反馈（暂不支持）"""
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get("/conversations")
async def list_conversations():
    """获取对话列表（暂不支持）"""
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get("/conversations/{conversation_id}/messages")
async def get_conversation_messages(conversation_id: str):
    """获取对话消息列表（暂不支持）"""
    raise HTTPException(status_code=501, detail="Not implemented")


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str):
    """删除对话（暂不支持）"""
    raise HTTPException(status_code=501, detail="Not implemented")
