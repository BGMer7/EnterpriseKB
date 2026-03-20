
import os

# --- 兼容新版 MinerU 的导入 ---
try:
    # 针对 magic-pdf (0.10.x - 1.x)
    from magic_pdf.tools.common import do_parse
except ImportError:
    # 针对最新更名的 mineru 包 (2.x)
    from mineru.cli.common import do_parse

# --- LangChain 相关导入 (保持不变) ---
from langchain_text_splitters import MarkdownHeaderTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma


def extract_pdf_with_mineru_latest(pdf_path: str, output_dir: str) -> str:
    """
    使用新版 MinerU 解析 PDF 并提取为 Markdown
    """
    print(f"🚀 开始使用最新版 MinerU 解析: {pdf_path}")
    
    file_name = os.path.splitext(os.path.basename(pdf_path))[0]
    os.makedirs(output_dir, exist_ok=True)
    
    # 1. 读取 PDF 字节流
    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()

    # 2. 设定解析模式
    # "auto": 自动识别是否需要 OCR
    # "ocr": 强制使用视觉 OCR 模型 (遇到纯扫描件研报时建议开启)
    parse_method = "auto" 

    # 3. 调用核心解析流水线
    # do_parse 会自动在 output_dir 下创建一个以 file_name 命名的文件夹，
    # 并把 md、json 和 images 全部写进去。
    do_parse(
        output_dir=output_dir,
        pdf_file_name=file_name,
        pdf_bytes_or_dataset=pdf_bytes,
        model_list=[],         # 传空列表会自动读取本地的 magic-pdf.json 配置
        parse_method=parse_method,
        debug_able=False
    )
    
    # 4. 获取生成的 Markdown 文件路径
    # 默认路径规则: output_dir / file_name / file_name.md
    md_path = os.path.join(output_dir, file_name, f"{file_name}.md")
    
    print(f"✅ 解析完成！数据已保存至: {os.path.join(output_dir, file_name)}")
    
    # 5. 读取并返回 Markdown 内容供下游 Embedding 使用
    with open(md_path, "r", encoding="utf-8") as f:
        return f.read()


def chunk_and_embed(markdown_text: str, collection_name: str = "financial_reports"):
    # ... 此处代码与之前完全一致 ...
    print("✂️ 开始根据 Markdown 层级进行语义切分...")
    
    headers_to_split_on = [
        ("#", "Header 1"),
        ("##", "Header 2"),
        ("###", "Header 3"),
    ]
    markdown_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=headers_to_split_on,
        strip_headers=False 
    )
    
    md_header_splits = markdown_splitter.split_text(markdown_text)
    print(f"📊 共切分为 {len(md_header_splits)} 个逻辑数据块 (Chunks)。")
    
    model_name = "BAAI/bge-large-zh-v1.5"
    model_kwargs = {'device': 'cpu'} # 如果有显卡可以换成 'cuda'
    encode_kwargs = {'normalize_embeddings': True}
    
    embeddings = HuggingFaceEmbeddings(
        model_name=model_name,
        model_kwargs=model_kwargs,
        encode_kwargs=encode_kwargs
    )
    
    persist_directory = "./chroma_db"
    vectorstore = Chroma.from_documents(
        documents=md_header_splits,
        embedding=embeddings,
        collection_name=collection_name,
        persist_directory=persist_directory
    )
    
    print(f"🎉 全部完成！向量数据库已持久化至: {persist_directory}")
    return vectorstore


if __name__ == "__main__":
    SAMPLE_PDF_PATH = os.path.join(os.path.dirname(__file__), "files", "1911.05722v3.pdf") 
    OUTPUT_DIR = "./mineru_output"
    
    if not os.path.exists(SAMPLE_PDF_PATH):
        print("⚠️ 找不到 PDF 文件，请检查路径。")
    else:
        # 1. 提取
        markdown_data = extract_pdf_with_mineru_latest(SAMPLE_PDF_PATH, OUTPUT_DIR)
        
        # 2. 分块与 Embedding
        db = chunk_and_embed(markdown_data)