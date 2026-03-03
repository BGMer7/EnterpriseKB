"""
解析用户提供的PDF文件，保存完整结果到文件
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.processors.parser import DocumentParser


def main():
    pdf_path = r"d:\Learning\Projects\EnterpriseKB\backend\tests\files\1911.05722v3.pdf"
    output_path = r"d:\Learning\Projects\EnterpriseKB\backend\tests\files\pdf_parse_result.txt"

    print(f"📄 解析文件: {pdf_path}")
    print("=" * 60)

    result = DocumentParser.parse(pdf_path, "pdf")

    # 构建完整输出
    output_lines = []
    output_lines.append("=" * 70)
    output_lines.append("PDF 解析结果")
    output_lines.append("=" * 70)
    output_lines.append(f"\n文件: {pdf_path}")
    output_lines.append(f"\n📊 元数据:")
    for key, value in result['metadata'].items():
        output_lines.append(f"   - {key}: {value}")

    output_lines.append(f"\n📝 完整内容:")
    output_lines.append("-" * 70)
    output_lines.append(result['content'])

    output_lines.append("\n\n" + "=" * 70)
    output_lines.append("逐页详情")
    output_lines.append("=" * 70)

    for page in result['pages']:
        output_lines.append(f"\n\n{'='*50}")
        output_lines.append(f"第 {page['page_number']} 页")
        output_lines.append(f"{'='*50}")
        output_lines.append(page['content'])

    # 写入文件
    output_content = "\n".join(output_lines)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(output_content)

    print(f"\n✅ 完整结果已保存到: {output_path}")
    print(f"   总字符数: {len(result['content'])}")
    print(f"   页数: {len(result['pages'])}")


if __name__ == "__main__":
    main()
