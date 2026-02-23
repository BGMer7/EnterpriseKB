"""
数据清洗器
清洗文档内容，去除噪声和无关信息
"""
import re
from typing import List, Dict, Any


class DocumentCleaner:
    """
    文档清洗器
    """

    @staticmethod
    def clean(content: str, options: Dict[str, Any] = None) -> str:
        """
        清洗文档内容

        Args:
            content: 原始内容
            options: 清洗选项 {
                "remove_page_numbers": bool,     # 去除页码
                "remove_headers": bool,         # 去除页眉
                "remove_footers": bool,         # 去除页脚
                "remove_whitespace": bool,      # 去除多余空白
                "normalize_quotes": bool,       # 规范化引号
                "remove_special_chars": bool,   # 去除特殊字符
            }

        Returns:
            str: 清洗后的内容
        """
        if options is None:
            options = {}

        cleaned = content

        # 去除页码
        if options.get("remove_page_numbers", True):
            cleaned = DocumentCleaner._remove_page_numbers(cleaned)

        # 去除页眉页脚
        if options.get("remove_headers", True):
            cleaned = DocumentCleaner._remove_headers_footers(cleaned)

        # 规范化空白
        if options.get("remove_whitespace", True):
            cleaned = DocumentCleaner._normalize_whitespace(cleaned)

        # 规范化引号
        if options.get("normalize_quotes", True):
            cleaned = DocumentCleaner._normalize_quotes(cleaned)

        # 去除特殊字符
        if options.get("remove_special_chars", False):
            cleaned = DocumentCleaner._remove_special_chars(cleaned)

        return cleaned

    @staticmethod
    def _remove_page_numbers(content: str) -> str:
        """
        去除页码

        Args:
            content: 内容

        Returns:
            str: 去除页码后的内容
        """
        # 匹配常见的页码格式
        patterns = [
            r'\n\s*-\s*\d+\s*-\s*\n',           # - 1 -
            r'\n\s*第\s*\d+\s*页\s*\n',       # 第 1 页
            r'\n\s*Page\s*\d+\s*\n',          # Page 1
            r'\n\s*P\.\s*\d+\s*\n',          # P. 1
        ]

        for pattern in patterns:
            content = re.sub(pattern, '\n', content)

        return content

    @staticmethod
    def _remove_headers_footers(content: str) -> str:
        """
        去除页眉页脚（简单实现）
        基于短行的模式识别

        Args:
            content: 内容

        Returns:
            str: 去除页眉页脚后的内容
        """
        lines = content.split('\n')
        filtered_lines = []

        for line in lines:
            line = line.strip()

            # 跳过空行
            if not line:
                continue

            # 跳过可能的页眉页脚（短行）
            # 规则：长度<10 且不包含中文标点
            if len(line) < 10 and not any(c in line for c in "。，！？"):
                continue

            filtered_lines.append(line)

        return '\n'.join(filtered_lines)

    @staticmethod
    def _normalize_whitespace(content: str) -> str:
        """
        规范化空白字符

        Args:
            content: 内容

        Returns:
            str: 规范化后的内容
        """
        # 去除多余空行（超过2个连续换行）
        content = re.sub(r'\n{3,}', '\n\n', content)

        # 去除行首行尾空格
        content = '\n'.join(line.strip() for line in content.split('\n'))

        # 统一空格
        content = re.sub(r' {2,}', ' ', content)

        return content

    @staticmethod
    def _normalize_quotes(content: str) -> str:
        """
        规范化引号

        Args:
            content: 内容

        Returns:
            str: 规范化后的内容
        """
        # 统一为中文引号
        content = content.replace('"', '"').replace('"', '"')
        content = content.replace("'", ''').replace("'", ''')

        return content

    @staticmethod
    def _remove_special_chars(content: str) -> str:
        """
        去除特殊字符

        Args:
            content: 内容

        Returns:
            str: 去除特殊字符后的内容
        """
        # 去除控制字符
        content = re.sub(r'[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f-\x9f]', '', content)

        return content

    @staticmethod
    def extract_text(content: str) -> str:
        """
        提取纯文本（去除Markdown、HTML等标记）

        Args:
            content: 内容

        Returns:
            str: 纯文本
        """
        # 去除Markdown标记
        content = re.sub(r'\*\*([^*]+)\*\*', r'\1', content)  # **bold**
        content = re.sub(r'\*([^*]+)\*', r'\1', content)     # *italic*
        content = re.sub(r'`([^`]+)`', r'\1', content)     # `code`

        # 去除HTML标签
        content = re.sub(r'<[^>]+>', '', content)

        return content


def clean_document(content: str, options: Dict[str, Any] = None) -> str:
    """
    清洗文档内容（便捷函数）

    Args:
        content: 原始内容
        options: 清洗选项

    Returns:
        str: 清洗后的内容
    """
    return DocumentCleaner.clean(content, options)
