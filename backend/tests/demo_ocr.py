"""
OCR功能演示脚本
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.processors.parser import DocumentParser


def main():
    pdf_path = r"d:\Learning\Projects\EnterpriseKB\backend\tests\files\1911.05722v3.pdf"

    print("=" * 60)
    print("PDF 解析对比测试（普通 vs OCR）")
    print("=" * 60)

    # 1. 普通解析
    print("\n📄 1. 普通解析（不启用OCR）:")
    print("-" * 40)
    result_normal = DocumentParser.parse(pdf_path, "pdf", use_ocr=False)
    print(f"   页数: {result_normal['metadata']['page_count']}")
    print(f"   字符数: {len(result_normal['content'])}")
    print(f"   前200字符:\n   {result_normal['content'][:200]}")

    # 2. OCR解析
    print("\n📄 2. OCR解析（启用OCR）:")
    print("-" * 40)
    print("   正在初始化PaddleOCR（首次较慢）...")

    # 第一次调用会初始化OCR引擎
    result_ocr = DocumentParser.parse(pdf_path, "pdf", use_ocr=True)
    print(f"   页数: {result_ocr['metadata']['page_count']}")
    print(f"   字符数: {len(result_ocr['content'])}")
    print(f"   OCR使用: {result_ocr['metadata'].get('ocr_used', False)}")
    print(f"   前200字符:\n   {result_ocr['content'][:200]}")

    # 对比
    print("\n📊 对比结果:")
    print("-" * 40)
    normal_len = len(result_normal['content'])
    ocr_len = len(result_ocr['content'])
    diff = ocr_len - normal_len
    print(f"   普通解析: {normal_len} 字符")
    print(f"   OCR解析:  {ocr_len} 字符")
    print(f"   差异:     {diff:+d} 字符")

    # 保存OCR结果
    output_path = r"d:\Learning\Projects\EnterpriseKB\backend\tests\files\pdf_ocr_result.txt"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("PDF OCR 解析结果\n")
        f.write("=" * 50 + "\n\n")
        f.write(result_ocr['content'])

    print(f"\n✅ OCR结果已保存到: {output_path}")


if __name__ == "__main__":
    main()
