"""
文档分块器
支持固定大小分块、语义分块、结构化分块、Markdown结构化分块
"""
from typing import List, Dict, Any, Optional
import re
from dataclasses import dataclass, field

# LangChain 分块器（可选依赖）
try:
    from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False
    MarkdownHeaderTextSplitter = None
    RecursiveCharacterTextSplitter = None


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


# ============================================================
# Markdown 结构化分块器（基于 LangChain）
# ============================================================

def _protect_tables(text: str) -> tuple[str, List[Dict]]:
    """
    保护表格不被切割，将表格单独存储
    支持 Markdown 表格和 HTML 表格

    Returns:
        (处理后的文本, 表格列表)
    """
    tables = []

    # 1. 匹配 Markdown 表格格式 |col|col|
    md_table_pattern = r'(\|([^\n|]+\|)+[\s\S]*?(?=\n\n|\n$|$))'

    # 2. 匹配 HTML 表格格式 <table>...</table>
    html_table_pattern = r'(<table[^>]*>[\s\S]*?</table>)'

    def replace_md_table(match):
        table_text = match.group(1)
        tables.append({"type": "markdown", "content": table_text})
        return f"__TABLE_{len(tables)-1}__"

    def replace_html_table(match):
        table_text = match.group(1)
        tables.append({"type": "html", "content": table_text})
        return f"__TABLE_{len(tables)-1}__"

    # 先处理 Markdown 表格
    protected_text = re.sub(md_table_pattern, replace_md_table, text)
    # 再处理 HTML 表格
    protected_text = re.sub(html_table_pattern, replace_html_table, protected_text)

    return protected_text, tables


def _restore_tables(text: str, tables: List[Dict]) -> str:
    """恢复表格占位符，Markdown 表格保持原样，HTML 表格转换为 Markdown"""
    for i, table in enumerate(tables):
        table_content = table["content"]
        table_type = table.get("type", "markdown")

        if table_type == "html":
            # HTML 表格转换为 Markdown 格式
            md_table = _html_table_to_markdown(table_content)
            text = text.replace(f"__TABLE_{i}__", md_table)
        else:
            # Markdown 表格保持原样
            text = text.replace(f"__TABLE_{i}__", table_content)

    return text


def _html_table_to_markdown(html_table: str) -> str:
    """将 HTML 表格转换为 Markdown 表格"""
    import re

    # 提取所有行
    rows = re.findall(r'<tr[^>]*>(.*?)</tr>', html_table, re.DOTALL)
    if not rows:
        return html_table

    md_rows = []
    for row in rows:
        # 提取单元格
        cells = re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', row, re.DOTALL)
        # 清理单元格内容（移除 HTML 标签）
        cells = [re.sub(r'<[^>]+>', '', c).strip().replace('\n', ' ').replace('\r', '') for c in cells]
        if cells:
            md_rows.append('|' + '|'.join(cells) + '|')

    # 添加分隔行
    if len(md_rows) > 1:
        header_row = md_rows[0]
        separator_count = header_row.count('|') - 1
        separators = '|' + '|'.join(['---'] * separator_count) + '|'
        md_rows.insert(1, separators)

    return '\n'.join(md_rows)


def _protect_formulas(text: str) -> str:
    """保护公式不被切割"""
    # 匹配 $...$ 和 $$...$$
    text = re.sub(r'\$\$[\s\S]+?\$\$', lambda m: f"__FORMULA_{hash(m.group())}__", text)
    text = re.sub(r'\$[^\$\n]+?\$', lambda m: f"__FORMULA_{hash(m.group())}__", text)
    return text


def markdown_chunk(
    document_id: str,
    content: str,
    pages: List[Dict[str, Any]] = None,
    chunk_size: int = 512,
    chunk_overlap: int = 64
) -> List[Dict[str, Any]]:
    """
    Markdown 文档分块（两阶段切割）

    第一阶段：按 Markdown 标题结构切割
    第二阶段：对过长块递归切割

    Args:
        document_id: 文档ID
        content: Markdown 文本内容
        pages: 页面信息列表（可选）
        chunk_size: 块大小（token）
        chunk_overlap: 块重叠大小

    Returns:
        List[Dict]: 分块结果列表
    """
    if not LANGCHAIN_AVAILABLE:
        raise ImportError("需要安装 langchain: pip install langchain")

    # 0. 预处理：保护特殊内容
    original_content = content
    content, tables = _protect_tables(content)
    content = _protect_formulas(content)

    # 1. 第一阶段：按 Markdown 标题切割
    headers_to_split_on = [
        ("#", "title"),
        ("##", "section"),
        ("###", "subsection"),
        ("####", "subsubsection"),
    ]

    md_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=headers_to_split_on,
        strip_headers=False
    )

    try:
        header_chunks = md_splitter.split_text(content)
    except Exception as e:
        # 如果 Markdown 解析失败，回退到普通分块
        print(f"  ⚠️ Markdown 分割失败，回退到固定分块: {e}")
        chunker = DocumentChunker(chunk_size, chunk_overlap)
        return chunker.chunk(document_id, original_content, pages or [], "fixed")

    # 2. 第二阶段：对过长块递归切割
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", "。", "！", "？", "；", " ", ""],
        length_function=lambda x: len(x) * 1.5  # 中文估算
    )

    # 3. 处理每个 header chunk
    chunks = []
    chunk_index = 0

    for i, doc in enumerate(header_chunks):
        # 获取 metadata
        metadata = dict(doc.metadata) if doc.metadata else {}

        # 检查长度是否需要二次切割
        text = doc.page_content
        text_length = len(text) * 1.5  # 估算 token

        if text_length > chunk_size * 1.5:
            # 需要二次切割
            sub_texts = text_splitter.split_text(text)
            for sub_text in sub_texts:
                # 继承父级 metadata
                sub_metadata = metadata.copy()

                # 恢复特殊内容
                sub_text = _restore_tables(sub_text, tables)

                chunks.append({
                    "chunk_id": f"{document_id}_chunk_{chunk_index}",
                    "document_id": document_id,
                    "content": sub_text,
                    "chunk_index": chunk_index,
                    "page_number": metadata.get("page_number"),
                    "section": sub_metadata.get("section") or sub_metadata.get("subsection"),
                    "metadata": {
                        "strategy": "markdown",
                        "title": sub_metadata.get("title"),
                        "section": sub_metadata.get("section"),
                        "subsection": sub_metadata.get("subsection"),
                        "headers": {k: v for k, v in sub_metadata.items() if k.startswith("header_")}
                    }
                })
                chunk_index += 1
        else:
            # 长度合适，直接使用
            # 恢复特殊内容
            text = _restore_tables(text, tables)

            chunks.append({
                "chunk_id": f"{document_id}_chunk_{chunk_index}",
                "document_id": document_id,
                "content": text,
                "chunk_index": chunk_index,
                "page_number": metadata.get("page_number"),
                "section": metadata.get("section") or metadata.get("subsection"),
                "metadata": {
                    "strategy": "markdown",
                    "title": metadata.get("title"),
                    "section": metadata.get("section"),
                    "subsection": metadata.get("subsection"),
                    "headers": {k: v for k, v in metadata.items() if k.startswith("header_")}
                }
            })
            chunk_index += 1

    # 4. 过滤过短的 chunk
    min_size = 50
    filtered_chunks = [c for c in chunks if len(c["content"]) >= min_size]

    # 重新编号
    for i, c in enumerate(filtered_chunks):
        c["chunk_id"] = f"{document_id}_chunk_{i}"
        c["chunk_index"] = i

    print(f"  ✓ Markdown 分块: {len(filtered_chunks)} 个 chunks")
    return filtered_chunks


def chunk_by_strategy(
    document_id: str,
    content: str,
    pages: List[Dict[str, Any]] = None,
    strategy: str = "fixed",
    chunk_size: int = 512,
    chunk_overlap: int = 50
) -> List[Dict[str, Any]]:
    """
    根据策略分块（统一入口）

    Args:
        document_id: 文档ID
        content: 文档内容
        pages: 页面信息列表
        strategy: 分块策略 (fixed, semantic, structural, markdown)
        chunk_size: 块大小
        chunk_overlap: 块重叠大小

    Returns:
        List[Dict]: 分块结果列表
    """
    if strategy == "markdown":
        return markdown_chunk(document_id, content, pages, chunk_size, chunk_overlap)
    else:
        chunker = DocumentChunker(chunk_size, chunk_overlap)
        return chunker.chunk(document_id, content, pages, strategy)
