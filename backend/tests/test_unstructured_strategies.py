"""测试 unstructured 不同策略"""
import os

from unstructured.partition.pdf import partition_pdf
from unstructured.documents.elements import Text, Table, Title, NarrativeText

# 测试 auto 策略（会自动选择）
print("=== Testing strategy='auto' ===")
elements = partition_pdf(
    filename='backend/tests/files/1911.05722v3.pdf',
    strategy='auto',
    infer_table_structure=True,
    languages=['eng']
)

print(f'Total elements: {len(elements)}')
for i, el in enumerate(elements[:15]):
    el_type = type(el).__name__
    text_preview = repr(el.text)[:100] if el.text else ""
    print(f'{i}: {el_type} | {text_preview}')

# 统计元素类型
from collections import Counter
type_counts = Counter(type(el).__name__ for el in elements)
print(f"\nElement type distribution: {dict(type_counts)}")

# 检查表格的 text_as_html
tables = [el for el in elements if type(el).__name__ == 'Table']
if tables:
    print(f"\n=== First table metadata ===")
    t = tables[0]
    print(f"text: {t.text[:100] if t.text else 'N/A'}...")
    if hasattr(t, 'metadata') and hasattr(t.metadata, 'text_as_html'):
        print(f"text_as_html available: {bool(t.metadata.text_as_html)}")
        if t.metadata.text_as_html:
            print(f"html preview: {t.metadata.text_as_html[:200]}...")
