"""
文档分块器
支持固定大小分块、语义分块、结构化分块
"""
from typing import List, Dict, Any, Optional
import re
from dataclasses import dataclass


@dataclass
class Chunk:
    """文档块"""
    id: str
    document_id: str
    content: str
    chunk_index: int
    page_number: Optional[int]
    section: Optional[str]
    metadata: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "chunk_id": self.id,
            "document_id": self.document_id,
            "content": self.content,
            "chunk_index": self.chunk_index,
            "page_number": self.page_number,
            "section": self.section,
            "metadata": self.metadata,
        }


class DocumentChunker:
    """
    文档分块器
    """

    def __init__(
        self,
        chunk_size: int = 512,  # tokens
        chunk_overlap: int = 50,
        min_chunk_size: int = 100
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size

    def chunk(
        self,
        document_id: str,
        content: str,
        pages: List[Dict[str, Any]],
        strategy: str = "fixed"
    ) -> List[Chunk]:
        """
        对文档进行分块

        Args:
            document_id: 文档ID
            content: 完整文档内容
            pages: 页面信息列表
            strategy: 分块策略 (fixed, semantic, structural)

        Returns:
            List[Chunk]: 文档块列表
        """
        chunkers = {
            "fixed": self._chunk_fixed,
            "semantic": self._chunk_semantic,
            "structural": self._chunk_structural,
        }

        chunker_func = chunkers.get(strategy, self._chunk_fixed)
        return chunker_func(document_id, content, pages)

    def _chunk_fixed(
        self,
        document_id: str,
        content: str,
        pages: List[Dict[str, Any]]
    ) -> List[Chunk]:
        """
        固定大小分块

        Args:
            document_id: 文档ID
            content: 文档内容
            pages: 页面信息列表

        Returns:
            List[Chunk]: 文档块列表
        """
        chunks = []
        chunk_index = 0

        # 按句子分割
        sentences = re.split(r'[。！?!.；;]', content)

        current_chunk = ""
        current_tokens = 0
        current_page = 0

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            # 估算token数（1汉字≈1.5token）
            sentence_tokens = len(sentence) * 1.5

            # 检查是否需要开始新的chunk
            if current_tokens + sentence_tokens > self.chunk_size:
                # 保存当前chunk
                if len(current_chunk) >= self.min_chunk_size:
                    chunks.append(Chunk(
                        id=self._generate_id(document_id, chunk_index),
                        document_id=document_id,
                        content=current_chunk,
                        chunk_index=chunk_index,
                        page_number=current_page + 1,
                        section=None,
                        metadata={"strategy": "fixed"}
                    ))
                    chunk_index += 1

                # 开始新chunk
                current_chunk = sentence + "。"
                current_tokens = sentence_tokens
            else:
                current_chunk += sentence + "。"
                current_tokens += sentence_tokens

        # 保存最后一个chunk
        if len(current_chunk) >= self.min_chunk_size:
            chunks.append(Chunk(
                id=self._generate_id(document_id, chunk_index),
                document_id=document_id,
                content=current_chunk,
                chunk_index=chunk_index,
                page_number=current_page + 1,
                section=None,
                metadata={"strategy": "fixed"}
            ))

        return chunks

    def _chunk_semantic(
        self,
        document_id: str,
        content: str,
        pages: List[Dict[str, Any]]
    ) -> List[Chunk]:
        """
        语义分块
        基于段落和语义相似度进行分块

        Args:
            document_id: 文档ID
            content: 文档内容
            pages: 页面信息列表

        Returns:
            List[Chunk]: 文档块列表
        """
        # 先按段落分割
        paragraphs = re.split(r'\n\n+', content)

        chunks = []
        chunk_index = 0

        current_chunk = ""
        current_tokens = 0

        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            if not paragraph:
                continue

            paragraph_tokens = len(paragraph) * 1.5

            # 检查是否需要合并到当前chunk
            if current_tokens + paragraph_tokens <= self.chunk_size:
                current_chunk += paragraph + "\n\n"
                current_tokens += paragraph_tokens
            else:
                # 保存当前chunk
                if len(current_chunk) >= self.min_chunk_size:
                    chunks.append(Chunk(
                        id=self._generate_id(document_id, chunk_index),
                        document_id=document_id,
                        content=current_chunk,
                        chunk_index=chunk_index,
                        page_number=self._get_page_for_chunk(current_chunk, pages),
                        section=None,
                        metadata={"strategy": "semantic"}
                    ))
                    chunk_index += 1

                # 检查是否需要分块当前段落
                if paragraph_tokens > self.chunk_size:
                    # 长段落，需要进一步分块
                    sub_chunks = self._split_long_chunk(document_id, paragraph, chunk_index, pages)
                    chunks.extend(sub_chunks)
                    chunk_index += len(sub_chunks)
                    current_chunk = ""
                    current_tokens = 0
                else:
                    current_chunk = paragraph + "\n\n"
                    current_tokens = paragraph_tokens

        # 保存最后一个chunk
        if len(current_chunk) >= self.min_chunk_size:
            chunks.append(Chunk(
                id=self._generate_id(document_id, chunk_index),
                document_id=document_id,
                content=current_chunk,
                chunk_index=chunk_index,
                page_number=self._get_page_for_chunk(current_chunk, pages),
                section=None,
                metadata={"strategy": "semantic"}
            ))

        return chunks

    def _chunk_structural(
        self,
        document_id: str,
        content: str,
        pages: List[Dict[str, Any]]
    ) -> List[Chunk]:
        """
        结构化分块
        基于文档结构（标题、章节）进行分块

        Args:
            document_id: 文档ID
            content: 文档内容
            pages: 页面信息列表

        Returns:
            List[Chunk]: 文档块列表
        """
        chunks = []
        chunk_index = 0

        # 识别标题（简单实现）
        lines = content.split('\n')

        current_section = None
        current_chunk = ""

        for line in lines:
            line = line.strip()

            # 检测标题（如 "第一章", "1.1", "一、"）
            if self._is_heading(line):
                # 保存上一个chunk
                if len(current_chunk) >= self.min_chunk_size:
                    chunks.append(Chunk(
                        id=self._generate_id(document_id, chunk_index),
                        document_id=document_id,
                        content=current_chunk,
                        chunk_index=chunk_index,
                        page_number=self._get_page_for_content(current_chunk, pages),
                        section=current_section,
                        metadata={"strategy": "structural"}
                    ))
                    chunk_index += 1

                current_section = line
                current_chunk = line + "\n"
            else:
                current_chunk += line + "\n"

        # 保存最后一个chunk
        if len(current_chunk) >= self.min_chunk_size:
            chunks.append(Chunk(
                id=self._generate_id(document_id, chunk_index),
                document_id=document_id,
                content=current_chunk,
                chunk_index=chunk_index,
                page_number=self._get_page_for_content(current_chunk, pages),
                section=current_section,
                metadata={"strategy": "structural"}
            ))

        return chunks

    def _split_long_chunk(
        self,
        document_id: str,
        text: str,
        start_index: int,
        pages: List[Dict[str, Any]]
    ) -> List[Chunk]:
        """
        分割过长的文本块

        Args:
            document_id: 文档ID
            text: 待分割的文本
            start_index: 起始索引
            pages: 页面信息列表

        Returns:
            List[Chunk]: 分割后的块列表
        """
        chunks = []
        current_chunk = ""
        current_tokens = 0

        # 按句子分割
        sentences = re.split(r'[。！?!.；;]', text)

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            sentence_tokens = len(sentence) * 1.5

            if current_tokens + sentence_tokens > self.chunk_size:
                if len(current_chunk) >= self.min_chunk_size:
                    chunks.append(Chunk(
                        id=self._generate_id(document_id, start_index),
                        document_id=document_id,
                        content=current_chunk,
                        chunk_index=start_index,
                        page_number=self._get_page_for_content(current_chunk, pages),
                        section=None,
                        metadata={"strategy": "semantic_split"}
                    ))
                    start_index += 1

                current_chunk = sentence + "。"
                current_tokens = sentence_tokens
            else:
                current_chunk += sentence + "。"
                current_tokens += sentence_tokens

        if len(current_chunk) >= self.min_chunk_size:
            chunks.append(Chunk(
                id=self._generate_id(document_id, start_index),
                document_id=document_id,
                content=current_chunk,
                chunk_index=start_index,
                page_number=self._get_page_for_content(current_chunk, pages),
                section=None,
                metadata={"strategy": "semantic_split"}
            ))

        return chunks

    def _is_heading(self, line: str) -> bool:
        """
        判断是否为标题

        Args:
            line: 文本行

        Returns:
            bool: 是否为标题
        """
        # 简单规则
        patterns = [
            r'^第[一二三四五六七八九十百]+章',  # 第X章
            r'^[一二三四五六七八九十]+、',     # 一、二、
            r'^\d+\.',                           # 1. 2.
            r'^\d+\.\d+',                         # 1.1 1.2
            r'^\([一二三四五六七八九十]+\)^[^。，]', # (一)开头
        ]

        for pattern in patterns:
            if re.match(pattern, line):
                return True

        return False

    def _get_page_for_chunk(self, chunk: str, pages: List[Dict[str, Any]]) -> Optional[int]:
        """
        根据chunk内容获取页码

        Args:
            chunk: 块内容
            pages: 页面信息列表

        Returns:
            Optional[int]: 页码
        """
        if not pages:
            return None

        # 查找包含chunk内容的页面
        for page in pages:
            if page.get("content") and chunk[:50] in page["content"]:
                return page.get("page_number")

        return None

    def _get_page_for_content(self, content: str, pages: List[Dict[str, Any]]) -> Optional[int]:
        """
        获取内容的页码
        """
        return self._get_page_for_chunk(content, pages)

    def _generate_id(self, document_id: str = None, chunk_index: int = None) -> str:
        """生成chunk ID，格式为 {document_id}_chunk_{chunk_index}"""
        if document_id is not None and chunk_index is not None:
            return f"{document_id}_chunk_{chunk_index}"
        # Fallback to UUID if document_id or chunk_index not provided
        import uuid
        return str(uuid.uuid4())


def chunk_document(
    document_id: str,
    content: str,
    pages: List[Dict[str, Any]],
    strategy: str = "fixed",
    chunk_size: int = 512,
    chunk_overlap: int = 50
) -> List[Dict[str, Any]]:
    """
    对文档进行分块（便捷函数）

    Args:
        document_id: 文档ID
        content: 文档内容
        pages: 页面信息列表
        strategy: 分块策略
        chunk_size: 块大小
        chunk_overlap: 块重叠大小

    Returns:
        List[Dict]: 分块结果列表
    """
    chunker = DocumentChunker(chunk_size, chunk_overlap)
    chunks = chunker.chunk(document_id, content, pages, strategy)
    return [c.to_dict() for c in chunks]
