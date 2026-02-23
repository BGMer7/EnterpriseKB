"""
文档解析器
支持PDF、Word、Excel、Markdown等格式的解析
"""
from typing import List, Dict, Any, Optional
from io import BytesIO
from pathlib import Path

import fitz  # PyMuPDF
from docx import Document as DocxDocument
from openpyxl import load_workbook
import markdown


class DocumentParser:
    """
    文档解析器基类
    """

    @staticmethod
    def parse(file_path: str, file_type: str) -> Dict[str, Any]:
        """
        解析文档

        Args:
            file_path: 文件路径
            file_type: 文件类型 (pdf, docx, xlsx, md, txt)

        Returns:
            Dict: {
                "content": str,
                "pages": List[Dict],  # 页面内容
                "metadata": Dict,    # 元数据
            }
        """
        parsers = {
            "pdf": DocumentParser._parse_pdf,
            "docx": DocumentParser._parse_docx,
            "xlsx": DocumentParser._parse_xlsx,
            "md": DocumentParser._parse_markdown,
            "txt": DocumentParser._parse_text,
        }

        parser_func = parsers.get(file_type.lower())
        if not parser_func:
            raise ValueError(f"Unsupported file type: {file_type}")

        return parser_func(file_path)

    @staticmethod
    def parse_bytes(content: bytes, file_type: str) -> Dict[str, Any]:
        """
        解析字节内容

        Args:
            content: 文件字节内容
            file_type: 文件类型

        Returns:
            Dict: 解析结果
        """
        # 临时保存到文件
        import tempfile
        import os

        suffix = f".{file_type}"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        try:
            result = DocumentParser.parse(tmp_path, file_type)
            return result
        finally:
            os.unlink(tmp_path)

    @staticmethod
    def _parse_pdf(file_path: str) -> Dict[str, Any]:
        """
        解析PDF文档
        """
        doc = fitz.open(file_path)
        pages = []
        full_content = []

        for page_num, page in enumerate(doc, 1):
            text = page.get_text()
            pages.append({
                "page_number": page_num,
                "content": text,
                "width": page.rect.width,
                "height": page.rect.height,
            })
            full_content.append(text)

        doc.close()

        return {
            "content": "\n\n".join(full_content),
            "pages": pages,
            "metadata": {
                "page_count": len(pages),
                "format": "PDF"
            }
        }

    @staticmethod
    def _parse_docx(file_path: str) -> Dict[str, Any]:
        """
        解析Word文档
        """
        doc = DocxDocument(file_path)
        pages = []
        full_content = []

        # 遍历段落
        current_page = {
            "page_number": 1,
            "content": "",
            "sections": []
        }

        for para in doc.paragraphs:
            text = para.text.strip()
            if not text:
                continue

            # 检测章节
            if para.style and "Heading" in str(para.style):
                section = {
                    "level": int(str(para.style).split()[-1]),
                    "text": text
                }
                current_page["sections"].append(section)

            current_page["content"] += text + "\n"

        pages.append(current_page)
        full_content.append(current_page["content"])

        return {
            "content": "\n\n".join(full_content),
            "pages": pages,
            "metadata": {
                "page_count": 1,
                "format": "DOCX"
            }
        }

    @staticmethod
    def _parse_xlsx(file_path: str) -> Dict[str, Any]:
        """
        解析Excel文档
        """
        wb = load_workbook(file_path, data_only=True)
        pages = []
        full_content = []

        for sheet_num, sheet_name in enumerate(wb.sheetnames):
            sheet = wb[sheet_name]
            sheet_content = []

            for row in sheet.iter_rows(values_only=True):
                row_text = "\t".join([str(cell) if cell is not None else "" for cell in row])
                sheet_content.append(row_text)

            pages.append({
                "page_number": sheet_num + 1,
                "sheet_name": sheet_name,
                "content": "\n".join(sheet_content)
            })

            full_content.extend(sheet_content)

        return {
            "content": "\n\n".join(full_content),
            "pages": pages,
            "metadata": {
                "page_count": len(pages),
                "format": "XLSX"
            }
        }

    @staticmethod
    def _parse_markdown(file_path: str) -> Dict[str, Any]:
        """
        解析Markdown文档
        """
        with open(file_path, "r", encoding="utf-8") as f:
            md_content = f.read()

        # 转换为HTML再提取文本
        # 这里简单处理，直接使用原始内容
        pages = [{
            "page_number": 1,
            "content": md_content
        }]

        return {
            "content": md_content,
            "pages": pages,
            "metadata": {
                "page_count": 1,
                "format": "Markdown"
            }
        }

    @staticmethod
    def _parse_text(file_path: str) -> Dict[str, Any]:
        """
        解析纯文本文档
        """
        with open(file_path, "r", encoding="utf-8") as f:
            text_content = f.read()

        pages = [{
            "page_number": 1,
            "content": text_content
        }]

        return {
            "content": text_content,
            "pages": pages,
            "metadata": {
                "page_count": 1,
                "format": "TXT"
            }
        }


def parse_document(file_path: str, file_type: str) -> Dict[str, Any]:
    """
    解析文档（便捷函数）

    Args:
        file_path: 文件路径
        file_type: 文件类型

    Returns:
        Dict: 解析结果
    """
    return DocumentParser.parse(file_path, file_type)


def parse_document_from_bytes(content: bytes, file_type: str) -> Dict[str, Any]:
    """
    解析文档字节内容（便捷函数）

    Args:
        content: 文件字节内容
        file_type: 文件类型

    Returns:
        Dict: 解析结果
    """
    return DocumentParser.parse_bytes(content, file_type)
