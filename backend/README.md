# EnterpriseKB Backend

企业内部制度查询助手后端服务

## 快速开始

### 安装依赖

```bash
pip install -r requirements/dev.txt
```

### 配置环境变量

复制 `.env.example` 到 `.env` 并修改配置：

```bash
cp .env.example .env
```

### 初始化数据库

```bash
python -m alembic upgrade head
python scripts/init_db.py
```

### 启动服务

```bash
python -m app.main
```

或使用 uvicorn：

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### API文档

启动服务后访问：
- Swagger UI: http://localhost:8000/api/docs
- ReDoc: http://localhost:8000/api/redoc

## 项目结构

```
backend/
├── app/
│   ├── main.py              # 应用入口
│   ├── config.py            # 配置管理
│   ├── dependencies.py      # 依赖注入
│   ├── api/v1/              # API路由
│   ├── core/                # 核心模块（安全、权限）
│   ├── models/              # 数据模型
│   ├── schemas/             # Pydantic Schema
│   ├── rag/                 # RAG核心
│   ├── processors/          # 文档处理
│   ├── integrations/        # 外部集成
│   ├── services/            # 业务服务
│   ├── middleware/          # 中间件
│   └── db/                  # 数据库
├── alembic/                 # 数据库迁移
├── scripts/                 # 脚本
└── requirements/            # 依赖管理
```

## 开发指南

### 数据库迁移

创建新迁移：

```bash
alembic revision --autogenerate -m "描述"
```

应用迁移：

```bash
alembic upgrade head
```

回滚迁移：

```bash
alembic downgrade -1
```

### 运行测试

```bash
pytest
```

### 代码格式化

```bash
black app/
ruff check app/ --fix
```

---

## 多模态文档解析

### 功能概述

多模态文档解析模块支持从 PDF、Word、PPT 等文档中自动提取图像、表格等非文本内容，并在文档分块时保持这些元素的语义完整性。

### 支持的格式

| 格式 | 文本提取 | 图像提取 | 表格提取 |
|------|----------|----------|----------|
| PDF | ✅ | ✅ | ✅ |
| Word (docx) | ✅ | ✅ | ✅ |
| PPT (pptx) | ✅ | ✅ | ❌ |
| Excel (xlsx) | ✅ | - | ✅ |
| 图片 (png/jpg) | ✅ (OCR) | - | - |

### 数据结构

#### 页面解析结果

```python
{
    "page_number": 1,
    "content": "页面文本内容...",
    "width": 595.0,
    "height": 842.0,
    "images": [
        {
            "id": "p1_img0",           # 图像ID: p{页码}_img{序号}
            "width": 800,
            "height": 600,
            "ext": "png",
            "size": 123456,
            "position": {               # 页面位置（可选）
                "x": 100.0,
                "y": 200.0,
                "width": 400.0,
                "height": 300.0
            }
        }
    ],
    "tables": [
        {
            "id": "p1_table0",         # 表格ID: p{页码}_table{序号}
            "row_count": 5,
            "col_count": 3,
            "data": [                  # 表格数据（二维数组）
                ["列1", "列2", "列3"],
                ["数据1", "数据2", "数据3"]
            ],
            "bbox": [x0, y0, x1, y1]  # 页面位置
        }
    ]
}
```

### 多模态分块策略

系统支持多种分块策略，会根据文档内容自动选择：

| 策略 | 说明 | 适用场景 |
|------|------|----------|
| `multimodal` | 综合策略，表格/图像优先 | 包含图表的文档（推荐） |
| `table_first` | 表格优先分块 | 财务报表、数据报表 |
| `image_text` | 图像与周围文本关联 | 手册、说明书 |
| `semantic` | 语义段落分块 | 长文档、论文 |
| `structural` | 结构感知分块 | 书籍、报告 |
| `fixed` | 固定长度分块 | 纯文本文档 |

### Chunk元数据结构

多模态分块后的 chunk 包含丰富的元数据：

```python
{
    "id": "chunk_xxx",
    "document_id": "doc_xxx",
    "chunk_index": 0,
    "chunk_type": "text|table|mixed|image",
    "content": "分块内容...",
    "page_number": 1,
    "metadata": {
        "chunk_type": "table",
        "page_number": 1,
        "section": "第一章 公司介绍",
        "images": [{"id": "p1_img0", "description": "..."}],
        "tables": [{"id": "p1_table0", "row_count": 5, "col_count": 3}]
    }
}
```

### API 接口

#### 1. 解析文档（含多模态）

```bash
POST /api/v1/parse/document
Content-Type: multipart/form-data

# 参数
file: <PDF文件>
use_ocr: false  # 是否使用OCR（对扫描件有效）
ocr_langs: "ch,en"  # OCR语言设置
```

响应示例：

```json
{
    "success": true,
    "content": "完整文本内容...",
    "pages": [
        {
            "page_number": 1,
            "content": "第一页文本...",
            "images": [{"id": "p1_img0", "width": 800, "height": 600}],
            "tables": [{"id": "p1_table0", "row_count": 3, "col_count": 2}]
        }
    ],
    "metadata": {"page_count": 144, "file_type": "pdf"}
}
```

#### 2. 简化版解析

```bash
POST /api/v1/parse/document/simple
# 仅返回纯文本
```

#### 3. 获取支持的文件类型

```bash
GET /api/v1/parse/supported-types
```

### 核心代码

#### 文档解析器

- `app/processors/parser.py` - 多格式文档解析
  - `_extract_images_from_pdf_page()` - PDF图像提取
  - `_extract_tables_from_pdf_page()` - PDF表格提取
  - `_extract_images_from_docx()` - Word图像提取

#### 多模态分块器

- `app/processors/multimodal_chunker.py` - 多模态分块策略
  - `multimodal_chunk_document()` - 主入口
  - `has_multimodal_content()` - 检测多模态内容

#### 文档服务

- `app/services/document_service.py` - 自动选择分块策略

### 效果对比

以144页年报（含148张图像、101个表格）测试：

| 指标 | 普通处理 | 多模态处理 | 提升 |
|------|----------|------------|------|
| Chunk数量 | 1397 | 1508 | +8% |
| 平均长度 | 283字符 | 303字符 | +7% |
| 表格块 | 0 | **95** | ✅ 完整保留 |
| 图像关联块 | 0 | **87** | ✅ 语义关联 |

**结论**：多模态处理完整保留了表格结构和图像-文本关联，显著提升检索质量。

### 使用示例

#### Python 调用

```python
from app.processors.parser import DocumentParser
from app.processors.multimodal_chunker import multimodal_chunk_document, has_multimodal_content

# 1. 解析文档
result = DocumentParser.parse("document.pdf", "pdf")

# 2. 检查是否有多模态内容
pages = result.get("pages", [])
if has_multimodal_content(pages):
    # 3. 使用多模态分块
    chunks = multimodal_chunk_document(
        document_id="doc_001",
        pages=pages,
        strategy="multimodal"
    )
else:
    # 4. 使用普通分块
    from app.processors.chunker import chunk_document
    chunks = chunk_document(
        document_id="doc_001",
        content=result["content"],
        pages=pages,
        strategy="fixed"
    )
```

#### 运行对比测试

```bash
python tests/test_comparison.py <PDF文件路径>
```

### 注意事项

1. **图像二进制**：当前只提取图像元数据（位置、尺寸），不保存图像二进制数据
2. **表格格式**：表格数据以二维数组形式存储，部分复杂表格可能格式略有差异
3. **OCR支持**：扫描件PDF需要设置 `use_ocr=True` 启用OCR
4. **性能**：多模态解析耗时约为纯文本解析的1.5-2倍
