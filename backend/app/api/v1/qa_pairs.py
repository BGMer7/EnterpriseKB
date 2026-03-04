"""
QA对管理相关API
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies import get_current_user, require_permission
from app.schemas.admin import ApiResponse
from app.models.user import User
from app.core.constants import Permissions

router = APIRouter()


@router.get("")
async def list_qa_pairs(
    page: int = 1,
    page_size: int = 20,
    search: Optional[str] = None,
    is_verified: Optional[bool] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    获取QA对列表
    """
    from app.services.qa_service import qa_service

    return await qa_service.list_qa_pairs(
        db=db,
        user=current_user,
        page=page,
        page_size=page_size,
        search=search,
        is_verified=is_verified
    )


@router.post("")
async def create_qa_pair(
    question: str,
    answer: str,
    document_id: Optional[str] = None,
    current_user: User = Depends(
        require_permission(Permissions.QA_CREATE)
    ),
    db: AsyncSession = Depends(get_db)
):
    """
    创建QA对
    """
    from app.services.qa_service import qa_service

    return await qa_service.create_qa_pair(
        db=db,
        user_id=str(current_user.id),
        question=question,
        answer=answer,
        document_id=document_id
    )


@router.put("/{qa_pair_id}")
async def update_qa_pair(
    qa_pair_id: str,
    question: Optional[str] = None,
    answer: Optional[str] = None,
    is_verified: Optional[bool] = None,
    current_user: User = Depends(
        require_permission(Permissions.QA_UPDATE)
    ),
    db: AsyncSession = Depends(get_db)
):
    """
    更新QA对
    """
    from app.services.qa_service import qa_service

    return await qa_service.update_qa_pair(
        db=db,
        qa_pair_id=qa_pair_id,
        user=current_user,
        question=question,
        answer=answer,
        is_verified=is_verified
    )


@router.delete("/{qa_pair_id}")
async def delete_qa_pair(
    qa_pair_id: str,
    current_user: User = Depends(
        require_permission(Permissions.QA_DELETE)
    ),
    db: AsyncSession = Depends(get_db)
):
    """
    删除QA对
    """
    from app.services.qa_service import qa_service

    await qa_service.delete_qa_pair(
        db=db,
        qa_pair_id=qa_pair_id,
        user=current_user
    )

    return ApiResponse(message="QA对删除成功")


@router.post("/{qa_pair_id}/approve")
async def approve_qa_pair(
    qa_pair_id: str,
    current_user: User = Depends(
        require_permission(Permissions.QA_APPROVE)
    ),
    db: AsyncSession = Depends(get_db)
):
    """
    审核通过QA对
    """
    from app.services.qa_service import qa_service

    await qa_service.approve_qa_pair(
        db=db,
        qa_pair_id=qa_pair_id,
        user_id=str(current_user.id)
    )

    return ApiResponse(message="QA对已通过审核")


@router.post("/auto-generate")
async def auto_generate_qa_pairs(
    document_id: str,
    count: int = 5,
    current_user: User = Depends(
        require_permission(Permissions.QA_CREATE)
    ),
    db: AsyncSession = Depends(get_db)
):
    """
    基于文档自动生成QA对
    """
    from app.services.qa_service import qa_service

    return await qa_service.auto_generate_qa_pairs(
        db=db,
        document_id=document_id,
        user_id=str(current_user.id),
        count=count
    )
