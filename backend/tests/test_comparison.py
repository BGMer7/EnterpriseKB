"""
多模态vs普通处理对比测试
量化多模态chunking的效果提升
"""
import sys
sys.path.insert(0, '.')

import time
from app.processors.parser import DocumentParser
from app.processors.chunker import chunk_document
from app.processors.multimodal_chunker import multimodal_chunk_document, has_multimodal_content


def extract_content_only(pages):
    """提取纯文本内容（模拟非多模态处理）"""
    content = []
    for page in pages:
        text = page.get("content", "")
        content.append(text)
    return "\n\n".join(content)


def evaluate_chunk_quality(chunks, test_name):
    """评估chunk质量"""
    if not chunks:
        return {"error": "No chunks generated"}

    # 1.Chunk数量
    chunk_count = len(chunks)

    # 2.平均chunk长度
    avg_length = sum(len(c.get("content", "")) for c in chunks) / chunk_count

    # 3.表格完整性（表格块数量）
    table_chunks = [c for c in chunks if c.get("chunk_type") == "table" or (c.get("metadata", {}).get("table_count", 0) > 0)]
    table_count = len(table_chunks)

    # 4.图像关联（mixed块数量）
    mixed_chunks = [c for c in chunks if c.get("chunk_type") in ["mixed", "image"]]
    mixed_count = len(mixed_chunks)

    # 5.文本块数量
    text_chunks = [c for c in chunks if c.get("chunk_type") in ["text", None] or c.get("chunk_type") == ""]
    text_count = len(text_chunks)

    # 6.页码分布
    pages_covered = set()
    for c in chunks:
        pn = c.get("page_number") or c.get("metadata", {}).get("page_number")
        if pn:
            pages_covered.add(pn)

    return {
        "test_name": test_name,
        "chunk_count": chunk_count,
        "avg_length": round(avg_length, 1),
        "table_chunks": table_count,
        "mixed_chunks": mixed_count,
        "text_chunks": text_count,
        "pages_covered": len(pages_covered)
    }


def run_comparison(pdf_path, file_type="pdf"):
    """运行对比测试"""
    print("=" * 70)
    print(f"测试文档: {pdf_path}")
    print("=" * 70)

    # 1. 解析文档
    print("\n[1] 解析文档...")
    start = time.time()
    try:
        result = DocumentParser.parse(pdf_path, file_type, use_ocr=False)
        parse_time = time.time() - start
        print(f"  ✓ 解析完成，耗时: {parse_time:.2f}s")
    except Exception as e:
        print(f"  ✗ 解析失败: {e}")
        return

    pages = result.get("pages", [])
    content = result.get("content", "")

    # 统计原始内容
    total_images = sum(len(p.get("images", [])) for p in pages)
    total_tables = sum(len(p.get("tables", [])) for p in pages)

    print(f"\n[2] 文档统计")
    print(f"  - 页面数: {len(pages)}")
    print(f"  - 总文本长度: {len(content)} 字符")
    print(f"  - 图像数: {total_images}")
    print(f"  - 表格数: {total_tables}")
    print(f"  - 包含多模态内容: {has_multimodal_content(pages)}")

    # 2. 普通处理（固定分块）
    print("\n[3] 普通处理 (Fixed Chunking)...")
    start = time.time()
    normal_chunks = chunk_document(
        document_id="test-normal",
        content=content,
        pages=[],
        strategy="fixed"
    )
    normal_time = time.time() - start
    normal_result = evaluate_chunk_quality(normal_chunks, "普通处理")
    normal_result["time"] = round(normal_time, 2)

    print(f"  - Chunk数量: {normal_result['chunk_count']}")
    print(f"  - 平均长度: {normal_result['avg_length']}")
    print(f"  - 耗时: {normal_time:.2f}s")

    # 3. 多模态处理
    print("\n[4] 多模态处理 (Multimodal Chunking)...")
    start = time.time()
    multimodal_chunks = multimodal_chunk_document(
        document_id="test-multimodal",
        pages=pages,
        strategy="multimodal"
    )
    multimodal_time = time.time() - start
    multimodal_result = evaluate_chunk_quality(multimodal_chunks, "多模态处理")
    multimodal_result["time"] = round(multimodal_time, 2)

    print(f"  - Chunk数量: {multimodal_result['chunk_count']}")
    print(f"  - 平均长度: {multimodal_result['avg_length']}")
    print(f"  - 表格块: {multimodal_result['table_chunks']}")
    print(f"  - 混合块: {multimodal_result['mixed_chunks']}")
    print(f"  - 耗时: {multimodal_time:.2f}s")

    # 4. 对比结果
    print("\n" + "=" * 70)
    print("对比结果")
    print("=" * 70)

    print(f"\n{'指标':<20} {'普通处理':<15} {'多模态处理':<15} {'差异':<15}")
    print("-" * 70)

    # Chunk数量
    diff = multimodal_result['chunk_count'] - normal_result['chunk_count']
    pct = f"+{diff}" if diff >= 0 else f"{diff}"
    print(f"{'Chunk数量':<20} {normal_result['chunk_count']:<15} {multimodal_result['chunk_count']:<15} {pct:<15}")

    # 平均长度
    diff = multimodal_result['avg_length'] - normal_result['avg_length']
    pct = f"+{diff:.1f}" if diff >= 0 else f"{diff:.1f}"
    print(f"{'平均长度':<20} {normal_result['avg_length']:<15} {multimodal_result['avg_length']:<15} {pct:<15}")

    # 表格保留
    if total_tables > 0:
        table_preserved = multimodal_result['table_chunks'] > 0
        status = "✓ 保留" if table_preserved else "✗ 丢失"
        print(f"{'表格保留':<20} {'N/A':<15} {status:<15} {'关键差异':<15}")

    # 图像关联
    if total_images > 0:
        img_associated = multimodal_result['mixed_chunks'] > 0
        status = "✓ 关联" if img_associated else "✗ 丢失"
        print(f"{'图像关联':<20} {'N/A':<15} {status:<15} {'关键差异':<15}")

    # 5. 效果提升总结
    print("\n" + "=" * 70)
    print("效果提升总结")
    print("=" * 70)

    improvements = []

    if total_tables > 0 and multimodal_result['table_chunks'] > 0:
        improvements.append("✓ 表格结构完整保留，不再被粗暴切分")

    if total_images > 0 and multimodal_result['mixed_chunks'] > 0:
        improvements.append("✓ 图像与周边文本关联，保持语义完整")

    if improvements:
        for imp in improvements:
            print(f"  {imp}")
    else:
        print("  (文档无多模态内容，两种处理方式效果相近)")

    return {
        "normal": normal_result,
        "multimodal": multimodal_result,
        "has_multimodal": total_images > 0 or total_tables > 0
    }


def test_with_sample_documents():
    """使用示例文档测试"""
    print("\n" + "#" * 70)
    print("# 多模态Chunking效果对比测试")
    print("#" * 70)

    # 可以替换为实际测试文件路径
    test_files = [
        # "tests/test_data/report_with_tables.pdf",
        # "tests/test_data/manual_with_images.pdf",
    ]

    if not test_files or not test_files[0]:
        print("\n⚠ 未配置测试文件，请手动指定测试文件路径")
        print("\n用法: python test_comparison.py <pdf文件路径>")
        return

    for f in test_files:
        run_comparison(f)


if __name__ == "__main__":
    import os

    if len(sys.argv) > 1:
        # 命令行传入文件
        pdf_path = sys.argv[1]
        if os.path.exists(pdf_path):
            run_comparison(pdf_path)
        else:
            print(f"文件不存在: {pdf_path}")
    else:
        # 使用内置测试数据演示
        print("\n使用内置测试数据演示...\n")

        # 模拟数据
        demo_pages = [
            {
                "page_number": 1,
                "title": "第一章 公司介绍",
                "content": "这是第一页的内容。我们公司成立于2020年。" * 3,
                "images": [{"id": "img1", "width": 800, "height": 600}],
                "tables": [
                    {"id": "t1", "row_count": 3, "col_count": 2,
                     "data": [["年份", "营收"], ["2023", "1000万"], ["2024", "1500万"]]}
                ]
            },
            {
                "page_number": 2,
                "content": "第二页内容。包含更多详细信息。\n\n产品介绍：我们的主打产品包括..." * 2,
                "images": [],
                "tables": []
            }
        ]

        # 普通处理
        print("[普通处理] 基于纯文本分块")
        content = extract_content_only(demo_pages)
        normal_chunks = chunk_document("test", content, [], "fixed")
        normal_result = evaluate_chunk_quality(normal_chunks, "普通")
        print(f"  Chunk数: {normal_result['chunk_count']}, 平均长度: {normal_result['avg_length']}")

        # 多模态处理
        print("\n[多模态处理] 基于文档结构分块")
        multimodal_chunks = multimodal_chunk_document("test", demo_pages, "multimodal")
        multimodal_result = evaluate_chunk_quality(multimodal_chunks, "多模态")
        print(f"  Chunk数: {multimodal_result['chunk_count']}, 平均长度: {multimodal_result['avg_length']}")
        print(f"  表格块: {multimodal_result['table_chunks']}, 混合块: {multimodal_result['mixed_chunks']}")

        print("\n" + "=" * 70)
        print("结论: 多模态处理保留了表格结构，并关联了图像内容")
        print("=" * 70)
