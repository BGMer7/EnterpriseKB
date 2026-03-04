"""
文档解析API
提供独立的文档解析服务接口
"""
import os
import tempfile
from typing import Optional
from fastapi import APIRouter, File, UploadFile, Form, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel

router = APIRouter(prefix="/parse", tags=["文档解析"])


class ParseResponse(BaseModel):
    """解析响应"""
    success: bool
    content: str
    pages: list
    metadata: dict
    error: Optional[str] = None


@router.post("/document", response_model=ParseResponse)
async def parse_document(
    file: UploadFile = File(...),
    use_ocr: bool = Form(False),
    ocr_langs: str = Form("ch,en")
):
    """
    解析文档接口

    支持格式: pdf, docx, doc, xlsx, pptx, ppt, md, txt, html, htm, rtf, png, jpg, jpeg, gif, bmp, tiff, webp

    参数:
        - file: 要解析的文件
        - use_ocr: 是否使用OCR (对PDF/图片有效，默认False)
        - ocr_langs: OCR语言设置，默认 'ch,en'
    """
    # 临时保存文件
    suffix = os.path.splitext(file.filename)[1] if file.filename else ".tmp"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp_path = tmp.name
        content = await file.read()
        tmp.write(content)

    try:
        # 解析文件
        file_type = suffix[1:].lower()  # 去掉点号

        # 动态导入避免循环依赖
        from app.processors.parser import DocumentParser

        result = DocumentParser.parse(
            file_path=tmp_path,
            file_type=file_type,
            use_ocr=use_ocr,
            ocr_langs=ocr_langs
        )

        return ParseResponse(
            success=True,
            content=result.get("content", ""),
            pages=result.get("pages", []),
            metadata=result.get("metadata", {})
        )

    except Exception as e:
        return ParseResponse(
            success=False,
            content="",
            pages=[],
            metadata={},
            error=str(e)
        )

    finally:
        # 清理临时文件
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


@router.post("/document/simple")
async def parse_document_simple(
    file: UploadFile = File(...),
    use_ocr: bool = Form(False)
):
    """
    简化版解析接口 - 仅返回文本内容

    返回纯文本，便于前端直接使用
    """
    suffix = os.path.splitext(file.filename)[1] if file.filename else ".tmp"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp_path = tmp.name
        content = await file.read()
        tmp.write(content)

    try:
        file_type = suffix[1:].lower()
        from app.processors.parser import DocumentParser

        result = DocumentParser.parse(
            file_path=tmp_path,
            file_type=file_type,
            use_ocr=use_ocr
        )

        return {
            "success": True,
            "text": result.get("content", ""),
            "page_count": result.get("metadata", {}).get("page_count", 1)
        }

    except Exception as e:
        return {
            "success": False,
            "text": "",
            "error": str(e)
        }

    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


@router.get("/supported-types")
async def get_supported_types():
    """
    获取支持的文档类型
    """
    from app.processors.parser import DocumentParser

    # 按类别分组
    types_by_category = {
        "文档": ["pdf", "docx", "doc", "md", "txt", "rtf", "html", "htm"],
        "表格": ["xlsx", "xls"],
        "演示文稿": ["pptx", "ppt"],
        "图片": ["png", "jpg", "jpeg", "gif", "bmp", "tiff", "webp"]
    }

    return {
        "supported_types": list(DocumentParser.SUPPORTED_TYPES.keys()),
        "types_by_category": types_by_category,
        "ocr_available": True  # PaddleOCR已集成
    }
