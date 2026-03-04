"""
多模态文档分块器
支持表格感知分块、图像-文字关联分块、跨页语义分块
"""
from typing import List, Dict, Any, Optional
import re
from dataclasses import dataclass, field
import uuid


@dataclass
class MultimodalChunk:
    """多模态文档块"""
    id: str
    document_id: str
    content: str
    chunk_index: int
    chunk_type: str  # text, table, image, chart, mixed
    page_number: Optional[int]
    section: Optional[str]
    metadata: Dict[str, Any] = field(default_factory=dict)
    images: List[Dict[str, Any]] = field(default_factory=list)
    tables: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "document_id": self.document_id,
            "content": self.content,
            "chunk_index": self.chunk_index,
            "chunk_type": self.chunk_type,
            "page_number": self.page_number,
            "section": self.section,
            "metadata": self.metadata,
            "images": self.images,
            "tables": self.tables,
        }


class MultimodalChunker:
    """
    多模态文档分块器

    支持以下分块策略：
    - multimodal: 综合策略（推荐）- 保持文本语义完整，表格独立成块，图像关联
    - table_first: 表格优先 - 表格作为独立块优先处理
    - image_text: 图像文字关联 - 图像与周围文本关联
    - semantic: 语义分块 - 基于段落和语义相似度
    - structural: 结构化分块 - 基于文档结构（标题、章节）
    """

    def __init__(
        self,
        chunk_size: int = 512,  # tokens
        chunk_overlap: int = 50,
        min_chunk_size: int = 100,
        table_min_rows: int = 2  # 最小表格行数
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size
        self.table_min_rows = table_min_rows

    def chunk(
        self,
        document_id: str,
        pages: List[Dict[str, Any]],
        strategy: str = "multimodal"
    ) -> List[MultimodalChunk]:
        """
        对多模态文档进行分块

        Args:
            document_id: 文档ID
            pages: 页面信息列表（包含images/tables）
            strategy: 分块策略

        Returns:
            List[MultimodalChunk]: 多模态文档块列表
        """
        strategies = {
            "multimodal": self._chunk_multimodal,
            "table_first": self._chunk_table_first,
            "image_text": self._chunk_image_text,
            "semantic": self._chunk_semantic,
            "structural": self._chunk_structural,
        }

        chunker_func = strategies.get(strategy, self._chunk_multimodal)
        return chunker_func(document_id, pages)

    def _chunk_multimodal(
        self,
        document_id: str,
        pages: List[Dict[str, Any]]
    ) -> List[MultimodalChunk]:
        """
        综合多模态分块策略：
        1. 表格作为独立块
        2. 图像与周围文本关联
        3. 文本按语义分块
        """
        chunks = []
        chunk_index = 0

        # 1. 先处理表格（表格独立成块）
        for page in pages:
            page_num = page.get("page_number", 1)
            tables = page.get("tables", [])

            for table in tables:
                if table.get("row_count", 0) >= self.table_min_rows:
                    table_chunk = self._create_table_chunk(
                        document_id=document_id,
                        table=table,
                        page_number=page_num,
                        chunk_index=chunk_index
                    )
                    chunks.append(table_chunk)
                    chunk_index += 1

        # 2. 处理图像-文本关联和纯文本
        for page in pages:
            page_num = page.get("page_number", 1)
            content = page.get("content", "")
            images = page.get("images", [])
            tables = page.get("tables", [])

            # 移除已处理的表格内容
            text_content = self._remove_table_content(content, tables)

            # 提取页面标题作为section
            section = page.get("title") or page.get("sections", [{}])[0].get("text")

            # 处理文本内容（按段落分块）
            text_chunks = self._chunk_text_by_paragraph(
                document_id=document_id,
                content=text_content,
                page_number=page_num,
                section=section,
                start_index=chunk_index
            )

            # 3. 将图像与最近的文本块关联
            if images and text_chunks:
                text_chunks = self._associate_images_with_chunks(
                    text_chunks, images, page_num
                )

            chunks.extend(text_chunks)
            chunk_index += len(text_chunks)

        return chunks

    def _chunk_table_first(
        self,
        document_id: str,
        pages: List[Dict[str, Any]]
    ) -> List[MultimodalChunk]:
        """
        表格优先分块策略：
        1. 所有表格作为独立块
        2. 剩余文本按语义分块
        """
        # 先提取所有表格
        all_tables = []
        for page in pages:
            page_num = page.get("page_number", 1)
            tables = page.get("tables", [])

            for table in tables:
                all_tables.append({
                    **table,
                    "page_number": page_num
                })

        # 按页码排序表格
        all_tables.sort(key=lambda x: x.get("page_number", 1))

        # 创建表格块
        chunks = []
        chunk_index = 0

        for table in all_tables:
            if table.get("row_count", 0) >= self.table_min_rows:
                table_chunk = self._create_table_chunk(
                    document_id=document_id,
                    table=table,
                    page_number=table.get("page_number", 1),
                    chunk_index=chunk_index
                )
                chunks.append(table_chunk)
                chunk_index += 1

        # 处理剩余文本
        text_chunks = self._chunk_all_text(
            document_id=document_id,
            pages=pages,
            start_index=chunk_index
        )
        chunks.extend(text_chunks)

        return chunks

    def _chunk_image_text(
        self,
        document_id: str,
        pages: List[Dict[str, Any]]
    ) -> List[MultimodalChunk]:
        """
        图像-文字关联分块策略：
        1. 图像与周围文本组合
        2. 剩余文本按段落分块
        """
        chunks = []
        chunk_index = 0

        for page in pages:
            page_num = page.get("page_number", 1)
            content = page.get("content", "")
            images = page.get("images", [])
            section = page.get("title")

            if not images:
                # 无图像，纯文本分块
                text_chunks = self._chunk_text_by_paragraph(
                    document_id=document_id,
                    content=content,
                    page_number=page_num,
                    section=section,
                    start_index=chunk_index
                )
                chunks.extend(text_chunks)
                chunk_index += len(text_chunks)
            else:
                # 有图像，将文本与图像关联
                page_chunks = self._chunk_with_image_association(
                    document_id=document_id,
                    content=content,
                    images=images,
                    page_number=page_num,
                    section=section,
                    start_index=chunk_index
                )
                chunks.extend(page_chunks)
                chunk_index += len(page_chunks)

        return chunks

    def _chunk_semantic(
        self,
        document_id: str,
        pages: List[Dict[str, Any]]
    ) -> List[MultimodalChunk]:
        """语义分块"""
        return self._chunk_all_text(document_id, pages, start_index=0)

    def _chunk_structural(
        self,
        document_id: str,
        pages: List[Dict[str, Any]]
    ) -> List[MultimodalChunk]:
        """结构化分块"""
        chunks = []
        chunk_index = 0

        current_section = None

        for page in pages:
            page_num = page.get("page_number", 1)
            content = page.get("content", "")
            lines = content.split('\n')

            for line in lines:
                line = line.strip()
                if not line:
                    continue

                # 检测标题
                if self._is_heading(line):
                    current_section = line

                # 检查是否需要开始新块
                if chunks and chunks[-1].chunk_type == "text" and not self._is_heading(line):
                    # 追加到上一个文本块
                    existing_content = chunks[-1].content
                    estimated_tokens = len(existing_content + line) * 1.5

                    if estimated_tokens <= self.chunk_size:
                        chunks[-1].content += "\n" + line
                        continue

                # 创建新块
                if len(line) >= self.min_chunk_size:
                    chunk = MultimodalChunk(
                        id=str(uuid.uuid4()),
                        document_id=document_id,
                        content=line,
                        chunk_index=chunk_index,
                        chunk_type="text",
                        page_number=page_num,
                        section=current_section,
                        metadata={"strategy": "structural"}
                    )
                    chunks.append(chunk)
                    chunk_index += 1

        return chunks

    def _chunk_text_by_paragraph(
        self,
        document_id: str,
        content: str,
        page_number: int,
        section: Optional[str],
        start_index: int
    ) -> List[MultimodalChunk]:
        """按段落分块"""
        chunks = []
        chunk_index = start_index

        # 按段落分割
        paragraphs = re.split(r'\n\n+', content)

        current_chunk = ""
        current_tokens = 0

        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            if not paragraph:
                continue

            paragraph_tokens = len(paragraph) * 1.5

            # 检查是否需要合并
            if current_tokens + paragraph_tokens <= self.chunk_size:
                current_chunk += paragraph + "\n\n"
                current_tokens += paragraph_tokens
            else:
                # 保存当前块
                if len(current_chunk) >= self.min_chunk_size:
                    chunks.append(MultimodalChunk(
                        id=str(uuid.uuid4()),
                        document_id=document_id,
                        content=current_chunk.strip(),
                        chunk_index=chunk_index,
                        chunk_type="text",
                        page_number=page_number,
                        section=section,
                        metadata={"strategy": "multimodal"}
                    ))
                    chunk_index += 1

                # 处理过长段落
                if paragraph_tokens > self.chunk_size:
                    sub_chunks = self._split_long_text(
                        document_id, paragraph, page_number, section, chunk_index
                    )
                    chunks.extend(sub_chunks)
                    chunk_index += len(sub_chunks)
                    current_chunk = ""
                    current_tokens = 0
                else:
                    current_chunk = paragraph + "\n\n"
                    current_tokens = paragraph_tokens

        # 保存最后一个块
        if len(current_chunk) >= self.min_chunk_size:
            chunks.append(MultimodalChunk(
                id=str(uuid.uuid4()),
                document_id=document_id,
                content=current_chunk.strip(),
                chunk_index=chunk_index,
                chunk_type="text",
                page_number=page_number,
                section=section,
                metadata={"strategy": "multimodal"}
            ))

        return chunks

    def _chunk_all_text(
        self,
        document_id: str,
        pages: List[Dict[str, Any]],
        start_index: int
    ) -> List[MultimodalChunk]:
        """处理所有文本（忽略图像和表格）"""
        all_chunks = []

        for page in pages:
            page_num = page.get("page_number", 1)
            content = page.get("content", "")
            section = page.get("title")

            # 移除表格内容
            tables = page.get("tables", [])
            text_content = self._remove_table_content(content, tables)

            chunks = self._chunk_text_by_paragraph(
                document_id=document_id,
                content=text_content,
                page_number=page_num,
                section=section,
                start_index=start_index
            )
            all_chunks.extend(chunks)
            start_index += len(chunks)

        return all_chunks

    def _create_table_chunk(
        self,
        document_id: str,
        table: Dict[str, Any],
        page_number: int,
        chunk_index: int
    ) -> MultimodalChunk:
        """创建表格块"""
        table_data = table.get("data", [])

        # 格式化表格内容
        table_text = self._format_table_text(table_data)

        return MultimodalChunk(
            id=str(uuid.uuid4()),
            document_id=document_id,
            content=table_text,
            chunk_index=chunk_index,
            chunk_type="table",
            page_number=page_number,
            section=None,
            metadata={
                "strategy": "multimodal",
                "table_id": table.get("id"),
                "row_count": table.get("row_count", 0),
                "col_count": table.get("col_count", 0)
            },
            tables=[{
                "id": table.get("id"),
                "row_count": table.get("row_count", 0),
                "col_count": table.get("col_count", 0),
                "data": table_data
            }]
        )

    def _format_table_text(self, table_data: List[List[str]]) -> str:
        """格式化表格为文本"""
        if not table_data:
            return ""

        lines = []
        for row in table_data:
            # 处理None值，将其转换为空字符串
            formatted_row = [str(cell) if cell is not None else "" for cell in row]
            lines.append(" | ".join(formatted_row))
        return "\n".join(lines)

    def _remove_table_content(
        self,
        content: str,
        tables: List[Dict[str, Any]]
    ) -> str:
        """从内容中移除表格内容（用于纯文本分块）"""
        # 简单实现：移除包含表格标记的行
        lines = content.split('\n')
        result_lines = []

        for line in lines:
            # 跳过表格标记行
            if '[表格]' in line:
                continue
            # 检查是否像表格行（多个竖线分隔）
            if ' | ' in line and len(line.split(' | ')) >= 2:
                continue
            result_lines.append(line)

        return '\n'.join(result_lines)

    def _associate_images_with_chunks(
        self,
        text_chunks: List[MultimodalChunk],
        images: List[Dict[str, Any]],
        page_number: int
    ) -> List[MultimodalChunk]:
        """将图像与最近的文本块关联"""
        if not images or not text_chunks:
            return text_chunks

        # 将图像分配给第一个文本块（简化实现）
        # 更复杂的实现可以根据图像位置找到最近的文本块
        if text_chunks:
            text_chunks[0].chunk_type = "mixed"
            text_chunks[0].images = images
            text_chunks[0].metadata["has_images"] = True
            text_chunks[0].metadata["image_count"] = len(images)

        return text_chunks

    def _chunk_with_image_association(
        self,
        document_id: str,
        content: str,
        images: List[Dict[str, Any]],
        page_number: int,
        section: Optional[str],
        start_index: int
    ) -> List[MultimodalChunk]:
        """带图像关联的分块"""
        chunks = []

        # 按段落分割
        paragraphs = re.split(r'\n\n+', content)

        current_chunk = MultimodalChunk(
            id=str(uuid.uuid4()),
            document_id=document_id,
            content="",
            chunk_index=start_index,
            chunk_type="mixed" if images else "text",
            page_number=page_number,
            section=section,
            images=images if len(chunks) == 0 else []
        )

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            if len(current_chunk.content) + len(para) > self.chunk_size * 2:
                # 保存当前块
                if current_chunk.content.strip():
                    chunks.append(current_chunk)
                    start_index += 1

                # 创建新块
                current_chunk = MultimodalChunk(
                    id=str(uuid.uuid4()),
                    document_id=document_id,
                    content=para,
                    chunk_index=start_index,
                    chunk_type="mixed" if images else "text",
                    page_number=page_number,
                    section=section,
                    images=[]
                )
            else:
                current_chunk.content += para + "\n\n"

        # 保存最后一个块
        if current_chunk.content.strip():
            # 将图像分配给最后一个有内容的块
            if not current_chunk.images and images:
                current_chunk.images = images
                current_chunk.chunk_type = "mixed"
            chunks.append(current_chunk)

        return chunks

    def _split_long_text(
        self,
        document_id: str,
        text: str,
        page_number: int,
        section: Optional[str],
        start_index: int
    ) -> List[MultimodalChunk]:
        """分割长文本"""
        chunks = []
        chunk_index = start_index

        # 按句子分割
        sentences = re.split(r'[。！?!.；;]', text)

        current_chunk = ""
        current_tokens = 0

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            sentence_tokens = len(sentence) * 1.5

            if current_tokens + sentence_tokens > self.chunk_size:
                if len(current_chunk) >= self.min_chunk_size:
                    chunks.append(MultimodalChunk(
                        id=str(uuid.uuid4()),
                        document_id=document_id,
                        content=current_chunk.strip(),
                        chunk_index=chunk_index,
                        chunk_type="text",
                        page_number=page_number,
                        section=section,
                        metadata={"strategy": "semantic_split"}
                    ))
                    chunk_index += 1

                current_chunk = sentence + "。"
                current_tokens = sentence_tokens
            else:
                current_chunk += sentence + "。"
                current_tokens += sentence_tokens

        if len(current_chunk) >= self.min_chunk_size:
            chunks.append(MultimodalChunk(
                id=str(uuid.uuid4()),
                document_id=document_id,
                content=current_chunk.strip(),
                chunk_index=chunk_index,
                chunk_type="text",
                page_number=page_number,
                section=section,
                metadata={"strategy": "semantic_split"}
            ))

        return chunks

    def _is_heading(self, line: str) -> bool:
        """判断是否为标题"""
        patterns = [
            r'^第[一二三四五六七八九十百]+章',
            r'^[一二三四五六七八九十]+、',
            r'^\d+\.',
            r'^\d+\.\d+',
            r'^#{1,6}\s+',  # Markdown标题
        ]

        for pattern in patterns:
            if re.match(pattern, line):
                return True

        return False


def multimodal_chunk_document(
    document_id: str,
    pages: List[Dict[str, Any]],
    strategy: str = "multimodal",
    chunk_size: int = 512,
    chunk_overlap: int = 50
) -> List[Dict[str, Any]]:
    """
    多模态文档分块（便捷函数）

    Args:
        document_id: 文档ID
        pages: 页面信息列表
        strategy: 分块策略
        chunk_size: 块大小
        chunk_overlap: 块重叠大小

    Returns:
        List[Dict]: 分块结果列表
    """
    chunker = MultimodalChunker(chunk_size, chunk_overlap)
    chunks = chunker.chunk(document_id, pages, strategy)
    return [c.to_dict() for c in chunks]


def has_multimodal_content(pages: List[Dict[str, Any]]) -> bool:
    """
    检查页面是否包含多模态内容

    Args:
        pages: 页面信息列表

    Returns:
        bool: 是否包含多模态内容
    """
    for page in pages:
        # 检查是否有图像
        images = page.get("images", [])
        if images:
            return True

        # 检查是否有表格
        tables = page.get("tables", [])
        for table in tables:
            if table.get("row_count", 0) >= 2:
                return True

    return False
