"""
文档管理相关API
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, status, File, UploadFile, Form
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies import (
    get_current_user,
    require_permission,
    require_admin
)
from app.schemas.document import (
    DocumentCreate, DocumentUpdate, DocumentResponse,
    DocumentListResponse, DocumentUploadResponse,
    ChunkResponse
)
from app.schemas.admin import ApiResponse
from app.models.user import User
from app.core.constants import Permissions

router = APIRouter()


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    department_id: Optional[str] = Form(None),
    is_public: bool = Form(False),
    allowed_roles: str = Form("[]"),  # JSON字符串
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    上传文档
    """
    from app.services.document_service import document_service
    import json

    return await document_service.upload_document(
        db=db,
        file=file,
        user_id=str(current_user.id),
        title=title,
        department_id=department_id,
        is_public=is_public,
        allowed_roles=json.loads(allowed_roles)
    )


@router.get("", response_model=DocumentListResponse)
async def list_documents(
    page: int = 1,
    page_size: int = 20,
    status: Optional[str] = None,
    department_id: Optional[str] = None,
    search: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    获取文档列表
    """
    from app.services.document_service import document_service

    return await document_service.list_documents(
        db=db,
        user=current_user,
        page=page,
        page_size=page_size,
        status=status,
        department_id=department_id,
        search=search
    )


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    获取文档详情
    """
    from app.services.document_service import document_service

    return await document_service.get_document(
        db=db,
        document_id=document_id,
        user=current_user
    )


@router.get("/{document_id}/chunks", response_model=List[ChunkResponse])
async def get_document_chunks(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    获取文档的分块列表
    """
    from app.services.document_service import document_service

    return await document_service.get_document_chunks(
        db=db,
        document_id=document_id,
        user=current_user
    )


@router.put("/{document_id}", response_model=DocumentResponse)
async def update_document(
    document_id: str,
    request: DocumentUpdate,
    current_user: User = Depends(
        require_permission(Permissions.DOCUMENT_EDIT)
    ),
    db: AsyncSession = Depends(get_db)
):
    """
    更新文档
    """
    from app.services.document_service import document_service

    return await document_service.update_document(
        db=db,
        document_id=document_id,
        user=current_user,
        update_data=request.model_dump(exclude_unset=True)
    )


@router.delete("/{document_id}")
async def delete_document(
    document_id: str,
    current_user: User = Depends(
        require_permission(Permissions.DOCUMENT_DELETE)
    ),
    db: AsyncSession = Depends(get_db)
):
    """
    删除文档
    """
    from app.services.document_service import document_service

    await document_service.delete_document(
        db=db,
        document_id=document_id,
        user=current_user
    )

    return ApiResponse(message="文档删除成功")


@router.post("/{document_id}/publish")
async def publish_document(
    document_id: str,
    current_user: User = Depends(
        require_permission(Permissions.DOCUMENT_AUDIT)
    ),
    db: AsyncSession = Depends(get_db)
):
    """
    发布文档
    """
    from app.services.document_service import document_service

    await document_service.publish_document(
        db=db,
        document_id=document_id,
        user_id=str(current_user.id)
    )

    return ApiResponse(message="文档已发布")


@router.post("/{document_id}/reject")
async def reject_document(
    document_id: str,
    comment: Optional[str] = None,
    current_user: User = Depends(
        require_permission(Permissions.DOCUMENT_AUDIT)
    ),
    db: AsyncSession = Depends(get_db)
):
    """
    拒绝文档
    """
    from app.services.document_service import document_service

    await document_service.reject_document(
        db=db,
        document_id=document_id,
        user_id=str(current_user.id),
        comment=comment
    )

    return ApiResponse(message="文档已拒绝")
