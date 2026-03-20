"""测试 unstructured hi_res 模式 + PaddleOCR"""
import os

# 设置环境变量（用于某些内部调用）
os.environ["OCR_AGENT"] = "unstructured.partition.utils.ocr_models.paddle_ocr"

from unstructured.partition.pdf import partition_pdf
from unstructured.partition.utils.constants import OCR_AGENT_PADDLE
from unstructured.documents.elements import Text, Table, Title, NarrativeText
from collections import Counter

print(f"OCR_AGENT constant: {OCR_AGENT_PADDLE}")

# 测试 hi_res 模式 + PaddleOCR（显式传递 ocr_agent 参数）
print("\n=== Testing hi_res with PaddleOCR ===")
elements = partition_pdf(
    filename='backend/tests/files/1911.05722v3.pdf',
    strategy='hi_res',
    infer_table_structure=True,
    languages=['en'],
    ocr_agent=OCR_AGENT_PADDLE,  # 显式传递
    table_ocr_agent=OCR_AGENT_PADDLE,  # 表格也用 PaddleOCR
)

print(f'Total elements: {len(elements)}')
for i, el in enumerate(elements[:20]):
    el_type = type(el).__name__
    text_preview = repr(el.text)[:100] if el.text else ""
    print(f'{i}: {el_type} | {text_preview}')

# 统计元素类型
type_counts = Counter(type(el).__name__ for el in elements)
print(f"\nElement type distribution: {dict(type_counts)}")

# 检查表格的 text_as_html
tables = [el for el in elements if type(el).__name__ == 'Table']
if tables:
    print(f"\n=== First table (text_as_html) ===")
    t = tables[0]
    print(f"text: {t.text[:150] if t.text else 'N/A'}...")
    if hasattr(t.metadata, 'text_as_html') and t.metadata.text_as_html:
        print(f"html preview:\n{t.metadata.text_as_html[:300]}...")
