"""
检索测试相关API
用于快速测试文档检索功能，无需认证
"""
import io
import tempfile
from typing import List, Optional
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.config import settings
from app.rag.retriever.vector_retriever import VectorRetriever
from app.rag.retriever.bm25_retriever import BM25Retriever
from app.rag.retriever.hybrid_retriever import HybridRetriever
from app.rag.embedding import encode_query
from app.integrations.milvus_client import get_milvus_client
from app.integrations.search_engine import get_meilisearch_client
from app.processors.parser import DocumentParser
from app.processors.chunker import chunk_document
from app.rag.embedding import encode_text

router = APIRouter()


class RetrievalRequest(BaseModel):
    """检索请求"""
    query: str
    top_k: int = 5


class RetrievalResult(BaseModel):
    """检索结果项"""
    content: str
    chunk_id: str
    document_id: str
    score: float
    document_title: Optional[str] = None


class RetrievalResponse(BaseModel):
    """检索响应"""
    query: str
    results: List[RetrievalResult]
    total: int


@router.post("/document")
async def process_document(
    file: UploadFile = File(...),
    chunk_strategy: str = Form("fixed"),
    chunk_size: int = Form(512)
):
    """
    处理文档：解析、分块、向量化并存入向量库
    """
    # 1. 读取文件内容
    content = await file.read()

    text_content = ""
    pages = []

    # 2. 解析文档
    try:
        # 根据文件类型解析
        if file.filename.endswith('.pdf'):
            # 保存到临时文件进行解析
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
                tmp.write(content)
                tmp_path = tmp.name

            parser = DocumentParser()
            result = parser.parse(tmp_path, file_type='pdf')
            # 注意：返回的是 content 不是 text
            text_content = result.get("content", "") or ""
            pages = result.get("pages", [])

        elif file.filename.endswith('.txt'):
            text_content = content.decode('utf-8')
            pages = []
        else:
            # 尝试通用解析
            with tempfile.NamedTemporaryFile(delete=False) as tmp:
                tmp.write(content)
                tmp_path = tmp.name

            # 从文件名提取文件类型
            ext = file.filename.split('.')[-1].lower() if '.' in file.filename else 'txt'
            parser = DocumentParser()
            result = parser.parse(tmp_path, file_type=ext)
            text_content = result.get("content", "") or ""
            pages = result.get("pages", [])

    except Exception as e:
        import traceback
        error_detail = f"解析失败: {str(e)}\n{traceback.format_exc()}"
        # 对于非txt文件，尝试直接解码为文本
        if not file.filename.endswith('.txt'):
            try:
                text_content = content.decode('utf-8')
                pages = []
            except:
                return JSONResponse(
                    status_code=400,
                    content={"error": error_detail}
                )
        else:
            return JSONResponse(
                status_code=400,
                content={"error": error_detail}
            )

    # 3. 分块
    print(f"DEBUG: filename={file.filename}, content_length={len(text_content) if text_content else 0}, pages={len(pages) if pages else 0}")

    if not text_content or len(text_content.strip()) == 0:
        return JSONResponse(
            status_code=400,
            content={"error": f"文档解析后内容为空。可能原因：1) PDF是图片扫描件，需要OCR 2) PDF加密 3) 文件损坏。原始内容长度: {len(text_content) if text_content else 0}"}
        )

    doc_id = f"test_{file.filename}"

    # 使用更小的 min_chunk_size 以支持小文档
    from app.processors.chunker import DocumentChunker
    chunker = DocumentChunker(chunk_size=chunk_size, chunk_overlap=50, min_chunk_size=20)
    chunks = chunker.chunk(doc_id, text_content, pages, chunk_strategy)
    chunks = [c.to_dict() for c in chunks]

    if not chunks:
        return JSONResponse(
            status_code=400,
            content={"error": f"文档内容为空或分块失败。内容长度: {len(text_content)}, 内容预览: {text_content[:200]}"}
        )

    # 4. 向量化并存入 Milvus
    try:
        milvus_client = get_milvus_client()
        collection_name = settings.MILVUS_COLLECTION_NAME

        # 检查 collection 是否存在，打印 schema
        try:
            if milvus_client.client.has_collection(collection_name):
                collection = milvus_client.client.describe_collection(collection_name)
                print(f"DEBUG: Collection '{collection_name}' schema: {collection}")

                # 打印字段信息
                fields = collection.get('fields', [])
                print(f"DEBUG: Fields:")
                for field in fields:
                    print(f"  - {field.get('name')}: {field.get('type')}, nullable={field.get('nullable')}, default={field.get('default_value')}")
        except Exception as e:
            print(f"DEBUG: Collection info error: {e}")

        # 批量向量化
        texts = [chunk["content"] for chunk in chunks]
        embeddings = encode_text(texts)
        print(f"DEBUG: embeddings generated, count: {len(embeddings)}")

        # 准备插入数据
        import time
        timestamp = int(time.time())
        insert_data = []
        for i, chunk in enumerate(chunks):
            insert_data.append({
                "chunk_id": chunk["chunk_id"],
                "document_id": doc_id,
                "content": chunk["content"],
                "embedding": embeddings[i].tolist() if hasattr(embeddings[i], 'tolist') else embeddings[i],
                "chunk_index": chunk["chunk_index"],
                "title": file.filename,
                "department_id": "",
                "is_public": True,
                "allowed_roles": [],
                "page_number": chunk.get("page_number", 0),
                "section": "",
                "created_at": timestamp,
                "metadata": {
                    "filename": file.filename,
                    "strategy": chunk_strategy
                }
            })

        # 批量插入
        milvus_client.insert_chunks(insert_data)

        return {
            "document_id": doc_id,
            "chunks_count": len(chunks),
            "status": "success"
        }
    except Exception as e:
        import traceback
        return JSONResponse(
            status_code=500,
            content={"error": f"向量存储失败: {str(e)}\n{traceback.format_exc()}"}
        )


@router.post("/search", response_model=RetrievalResponse)
async def retrieval_test(request: RetrievalRequest):
    """
    测试检索功能
    根据问题检索相关文档
    """
    import time
    start_time = time.time()

    try:
        # 1. 向量化查询
        t1 = time.time()
        query_embedding = encode_query(request.query)
        t2 = time.time()
        print(f"[TIMING] Step 1 - encode_query: {t2-t1:.3f}s")
        print(f"DEBUG: query='{request.query}', embedding shape: {len(query_embedding)}")

        # 2. 获取 Milvus 客户端
        t3 = time.time()
        milvus_client = get_milvus_client()
        t4 = time.time()
        print(f"[TIMING] Step 2 - get_milvus_client: {t4-t3:.3f}s")
        print(f"DEBUG: searching in collection: {milvus_client.collection_name}")

        # 3. 执行检索
        t5 = time.time()
        search_results = milvus_client.search(
            query_embedding=query_embedding,
            top_k=request.top_k,
            output_fields=["chunk_id", "document_id", "content", "metadata", "title"]
        )
        t6 = time.time()
        print(f"[TIMING] Step 3 - milvus_client.search: {t6-t5:.3f}s")
        print(f"DEBUG: search results count: {len(search_results) if search_results else 0}")
        if search_results:
            print(f"DEBUG: first result: {search_results[0]}")

        # 4. 整理结果
        t7 = time.time()
        results = []
        if search_results and len(search_results) > 0:
            for item in search_results:
                results.append(RetrievalResult(
                    content=item.get("content", ""),
                    chunk_id=item.get("chunk_id", ""),
                    document_id=item.get("document_id", ""),
                    score=item.get("score", 0),
                    document_title=item.get("title", "")
                ))
        t8 = time.time()
        print(f"[TIMING] Step 4 - format results: {t8-t7:.3f}s")

        total_time = time.time() - start_time
        print(f"[TIMING] TOTAL: {total_time:.3f}s")

        return RetrievalResponse(
            query=request.query,
            results=results,
            total=len(results)
        )

    except Exception as e:
        import traceback
        print(f"DEBUG: search error: {e}")
        print(f"DEBUG: traceback: {traceback.format_exc()}")
        return RetrievalResponse(
            query=request.query,
            results=[],
            total=0
        )


@router.get("/collections")
async def list_collections():
    """
    查看向量库中的文档
    """
    try:
        milvus_client = get_milvus_client()
        # 获取 collection 信息
        collections = milvus_client.list_collections()
        return {"collections": collections}
    except Exception as e:
        return {"error": str(e)}


@router.delete("/collections/{collection_name}")
async def clear_collection(collection_name: str):
    """
    清空指定 collection 的数据
    """
    try:
        milvus_client = get_milvus_client()
        milvus_client.drop_collection(collection_name=collection_name)
        return {"status": "success", "message": f"Collection {collection_name} 已清空"}
    except Exception as e:
        return {"error": str(e)}
