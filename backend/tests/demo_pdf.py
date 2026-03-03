"""
解析用户提供的PDF文件演示
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.processors.parser import DocumentParser


def main():
    pdf_path = r"d:\Learning\Projects\EnterpriseKB\backend\tests\files\1911.05722v3.pdf"

    print(f"📄 解析文件: {pdf_path}")
    print("=" * 60)

    result = DocumentParser.parse(pdf_path, "pdf")

    print(f"\n📊 元数据:")
    print(f"   - 格式: {result['metadata']['format']}")
    print(f"   - 页数: {result['metadata']['page_count']}")

    print(f"\n📝 内容预览:")
    print("-" * 40)

    content = result['content']
    print(f"总字符数: {len(content)}")
    print(f"\n前2000字符:")
    print(content[:2000])

    print("\n" + "-" * 40)
    print(f"\n📑 页面详情:")

    for page in result['pages']:
        print(f"\n--- 第 {page['page_number']} 页 ---")
        page_content = page['content'][:300] if page['content'] else "(空)"
        print(page_content)
        if len(page['content']) > 300:
            print("...")


if __name__ == "__main__":
    main()
