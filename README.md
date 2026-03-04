# EnterpriseKB - 企业内部制度查询助手 (RAG Chatbot)

> 基于RAG（检索增强生成）技术的企业内部制度智能问答系统，为员工提供7x24小时制度查询服务，支持企业微信Bot集成，数据完全本地私有化部署。

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11+-green.svg)](https://www.python.org/)
[![Node](https://img.shields.io/badge/node-18+-green.svg)](https://nodejs.org/)
[![Next.js](https://img.shields.io/badge/Next.js-14-black.svg)](https://nextjs.org/)

---

## 目录

- [功能特性](#功能特性)
- [技术架构](#技术架构)
- [核心设计](#核心设计)
- [技术细节](#技术细节)
- [快速开始](#快速开始)
- [开发指南](#开发指南)
- [部署指南](#部署指南)
- [API文档](#api文档)
- [常见问题](#常见问题)
- [贡献指南](#贡献指南)

---

## 功能特性

### 核心功能

| 功能 | 描述 |
|------|------|
| **智能问答** | 基于RAG技术，准确回答企业制度相关问题 |
| **混合检索** | 向量检索 + 全文检索（BM25）融合，提高召回率 |
| **引用溯源** | 每次回答附带文档来源，支持点击查看原文 |
| **多轮对话** | 支持上下文理解的多轮追问 |
| **流式响应** | 实时显示生成过程，提升用户体验 |
| **预设问题** | 热门问题快速入口，降低使用门槛 |
| **反馈机制** | 用户可对回答进行评价，持续优化效果 |
| **防幻觉检测** | 事实核查机制，确保答案准确性 |
| **多模态解析** | 自动提取图像、表格，保持语义完整 |

### 后台管理

| 模块 | 功能 |
|------|------|
| **文档管理** | 多格式文档上传、版本管理、审核流程、批量处理 |
| **QA对管理** | 基于LLM自动生成QA对、人工审核维护 |
| **用户权限** | RBAC权限控制、部门隔离、角色管理 |
| **数据看板** | 问答统计、热门问题、无答案汇总、运营分析 |
| **系统设置** | 模型配置、参数调优、系统集成 |

### 技术特点

- **🔒 数据安全**：数据完全本地存储，不出企业内网
- **⚡ 高性能**：支持百级并发，首字响应<2秒，完整响应<5秒
- **🎯 精准检索**：混合检索 + BGE重排序 + 权限过滤
- **🤖 中文优化**：Qwen2.5-14B + BGE-M3，针对中文场景优化
- **📱 企业微信**：原生集成，扫码登录，Bot对话
- **🔧 易于部署**：Docker Compose一键启动，完整健康检查
- **🖼️ 多模态支持**：表格结构完整保留，图像与文本语义关联

---

## 技术架构

### 整体架构图

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              用户层                                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │   Web端     │  │  企业微信Bot  │  │   管理后台  │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└─────────────────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           接入层 (Nginx + SSL)                              │
└─────────────────────────────────────────────────────────────────────────────────┘
                                  │
                    ┌─────────────┼─────────────┐
                    │             │             │
                    ▼             ▼             ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                        应用层                                          │
│  ┌─────────────────────────┐    ┌─────────────────────────┐        │
│  │   FastAPI Backend      │    │   Next.js Frontend     │        │
│  │   (Python 3.11)       │    │   (TypeScript)          │        │
│  │   - RESTful API        │    │   - SSR/ISR            │        │
│  │   - WebSocket(SSE)     │    │   - Component化          │        │
│  │   - 认证中间件          │    │   - 响应式设计          │        │
│  └─────────────────────────┘    └─────────────────────────┘        │
└─────────────────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                      业务服务层                                        │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐    │
│  │ 认证服务 │ │ 对话服务 │ │ 文档服务 │ │ 审计服务 │    │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘    │
└─────────────────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                      RAG核心层                                        │
│  ┌─────────────────────────────────────────────────────────────┐         │
│  │                  RAG Pipeline                          │         │
│  │  Query → 预处理 → 混合检索 → 融合 → 重排序 →      │         │
│  │  上下文构建 → LLM生成 → 后处理 → 流式输出            │         │
│  └─────────────────────────────────────────────────────────────┘         │
│                                                                │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ │
│  │ 向量检索器│ │ BM25检索器│ │ 混合检索器│ │ BGE重排序 │ │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘ │
│                                                                │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐            │
│  │ 引用生成  │ │ 幻觉检测  │ │ Prompt构建 │            │
│  └──────────┘ └──────────┘ └──────────┘            │
└─────────────────────────────────────────────────────────────────────────────────┘
                                  │
                    ┌─────────────┼─────────────┐
                    │             │             │
                    ▼             ▼             ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                       数据与AI层                                     │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │
│  │PostgreSQL │ │  Redis   │ │  Milvus  │ │Meilisearch│  │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘  │
│                                                                │
│  ┌─────────────────────────────┐ ┌────────────┐             │
│  │   vLLM Server             │ │   MinIO    │             │
│  │   Qwen2.5-14B-Instruct   │ │   对象存储  │             │
│  │   AWQ量化 24GB显存          │ │            │             │
│  └─────────────────────────────┘ └────────────┘             │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### 技术栈

#### 后端

| 组件 | 技术 | 版本 | 说明 |
|------|------|------|------|
| **Web框架** | FastAPI | 0.104+ | 异步高性能，自动API文档 |
| **Python** | Python | 3.11+ | 类型提示，异步支持 |
| **ORM** | SQLAlchemy | 2.0+ | 异步ORM，支持PostgreSQL |
| **数据库** | PostgreSQL | 16 | 关系型数据库，JSONB支持 |
| **向量数据库** | Milvus | 2.3+ | HNSW索引，权限过滤 |
| **全文搜索** | Meilisearch | 1.5+ | BM25优化，中文分词 |
| **LLM推理** | vLLM | 0.4+ | OpenAI兼容API，流式输出 |
| **Embedding** | BGE-M3 | FlagEmbed | 1024维，多语言支持 |
| **Reranker** | BGE-Reranker | FlagEmbed | 结果重排序 |
| **缓存** | Redis | 7+ | 会话管理，分布式锁 |
| **对象存储** | MinIO | RELEASE.2024+ | S3兼容，私有部署 |
| **消息队列** | RabbitMQ | 3.12+ | 异步任务处理 |

#### 前端

| 组件 | 技术 | 版本 | 说明 |
|------|------|------|------|
| **框架** | Next.js | 14 | App Router，SSR/ISR |
| **语言** | TypeScript | 5+ | 类型安全 |
| **样式** | Tailwind CSS | 3+ | 原子化CSS |
| **组件库** | shadcn/ui | Latest | Radix UI + Tailwind |
| **状态管理** | Zustand | 4+ | 轻量级状态管理 |
| **HTTP客户端** | axios | 1.6+ | 请求拦截，错误处理 |
| **图标** | lucide-react | Latest | 统一图标风格 |

---

## 核心设计

### RAG Pipeline设计

#### 流程图

```
用户查询 (User Query)
    │
    ▼
┌─────────────────────┐
│  Query Preprocessor  │
│  - 分词标准化          │
│  - 同义词扩展          │
│  - 意图识别          │
└─────────────────────┘
    │
    ├───────────────┬──────────────┐
    │               │              │
    ▼               ▼              ▼
┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│ Milvus检索  │ │Meilisearch │ │ 缓存检索    │
│ Top-K=30   │ │ Top-K=30   │ │ 命中即返回  │
│ 向量相似度   │ │ BM25分数   │ │             │
└─────────────┘ └─────────────┘ └─────────────┘
    │               │              │
    └───────────────┴──────────────┘
                    │
                    ▼
          ┌─────────────────┐
          │  RRF融合引擎    │
          │  Reciprocal    │
          │  Rank Fusion    │
          └─────────────────┘
                    │
                    ▼
          ┌─────────────────┐
          │ 权限过滤器      │
          │ - 部门隔离      │
          │ - 角色过滤      │
          │ - 公开文档      │
          └─────────────────┘
                    │
                    ▼
          ┌─────────────────┐
          │ BGE重排序      │
          │ Top-K=15      │
          │ 交叉编码器      │
          └─────────────────┘
                    │
                    ▼
          ┌─────────────────┐
          │ 上下文构建器    │
          │ - 按段落拼接    │
          │ - 去重处理      │
          │ - 长度控制      │
          └─────────────────┘
                    │
                    ▼
          ┌─────────────────┐
          │  Prompt构建器   │
          │ - 系统提示      │
          │ - 上下文注入    │
          │ - 用户查询      │
          └─────────────────┘
                    │
                    ▼
          ┌─────────────────┐
          │  LLM生成器      │
          │  Qwen2.5-14B  │
          │  流式输出(SSE)  │
          └─────────────────┘
                    │
                    ▼
          ┌─────────────────┐
          │  后处理器       │
          │ - 引用标注      │
          │ - 事实核查      │
          │ - 格式化输出    │
          └─────────────────┘
                    │
                    ▼
              流式响应给用户
```

#### 关键算法

##### 1. RRF（Reciprocal Rank Fusion）

```python
def rrf_fusion(results: List[List[Result]], k: int = 60) -> List[Result]:
    """
    RRF融合算法，整合多个检索结果
    """
    scores = {}  # {doc_id: rrf_score}
    for rank_list in results:
        for rank, result in enumerate(rank_list, start=1):
            doc_id = result.id
            if doc_id not in scores:
                scores[doc_id] = 0
            # RRF公式: 1 / (k + rank)
            scores[doc_id] += 1 / (k + rank)

    # 按分数排序返回
    return sorted(results, key=lambda x: scores[x.id], reverse=True)
```

##### 2. 权限感知检索

```python
def build_permission_filter(user: User) -> str:
    """
    构建Milvus权限过滤表达式
    """
    conditions = []

    # 公开文档
    conditions.append("is_public == true")

    # 用户部门
    if user.department_id:
        conditions.append(f'department_id == "{user.department_id}"')

    # 用户角色
    if user.roles:
        role_list = ",".join([f'"{role}"' for role in user.roles])
        conditions.append(f"allowed_roles in [{role_list}]")

    # 组合条件：OR关系
    return " || ".join(conditions)
```

##### 3. BGE重排序

```python
def bge_rerank(query: str, docs: List[Document], top_k: int = 15):
    """
    使用BGE Reranker重排序
    """
    pairs = [[query, doc.content] for doc in docs]
    scores = reranker_model.compute_score(pairs)

    for i, doc in enumerate(docs):
        doc.rerank_score = float(scores[i])

    return sorted(docs, key=lambda x: x.rerank_score, reverse=True)[:top_k]
```

### 数据库设计

#### 核心表结构

```sql
-- 用户表
CREATE TABLE users (
    id UUID PRIMARY KEY,
    wechat_id VARCHAR(64) UNIQUE,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(255),
    department_id UUID REFERENCES departments(id),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 文档表
CREATE TABLE documents (
    id UUID PRIMARY KEY,
    title VARCHAR(500) NOT NULL,
    file_name VARCHAR(255) NOT NULL,
    file_path TEXT NOT NULL,
    department_id UUID REFERENCES departments(id),
    is_public BOOLEAN DEFAULT FALSE,
    allowed_roles JSONB DEFAULT '[]',
    status VARCHAR(20) DEFAULT 'draft',
    version INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 文档块表（与Milvus同步）
CREATE TABLE chunks (
    id UUID PRIMARY KEY,
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',
    milvus_id VARCHAR(64),
    UNIQUE(document_id, chunk_index)
);

-- QA对表
CREATE TABLE qa_pairs (
    id UUID PRIMARY KEY,
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    document_id UUID REFERENCES documents(id),
    chunk_ids UUID[] DEFAULT '{}',
    is_verified BOOLEAN DEFAULT FALSE,
    usage_count INTEGER DEFAULT 0
);

-- 对话表
CREATE TABLE conversations (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(200),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 消息表
CREATE TABLE messages (
    id UUID PRIMARY KEY,
    conversation_id UUID REFERENCES conversations(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL,
    content TEXT NOT NULL,
    sources JSONB DEFAULT '[]',
    feedback VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Milvus Collection配置

```python
from pymilvus import FieldSchema, CollectionSchema, DataType

fields = [
    FieldSchema(name="id", dtype=DataType.VARCHAR, max_length=64, is_primary=True),
    FieldSchema(name="chunk_id", dtype=DataType.VARCHAR, max_length=64),
    FieldSchema(name="document_id", dtype=DataType.VARCHAR, max_length=64),
    FieldSchema(name="content", dtype=DataType.VARCHAR, max_length=65535),
    FieldSchema(name="title", dtype=DataType.VARCHAR, max_length=500),
    FieldSchema(name="department_id", dtype=DataType.VARCHAR, max_length=64),
    FieldSchema(name="is_public", dtype=DataType.BOOL),
    FieldSchema(name="allowed_roles", dtype=DataType.ARRAY, max_capacity=10,
              element_type=DataType.VARCHAR, max_length=50),
    FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=1024),  # BGE-M3维度
]

schema = CollectionSchema(fields, description="Enterprise documents")

# HNSW索引 - 适合高维向量
index_params = {
    "index_type": "HNSW",
    "metric_type": "COSINE",
    "params": {"M": 16, "efConstruction": 100}
}

# 标量索引 - 用于权限过滤
scalar_index_params = [
    {"field_name": "department_id", "index_type": "INVERTED"},
    {"field_name": "is_public", "index_type": "BITMAP"},
]
```

---

## 技术细节

### 1. 文档处理流程

```
文件上传
    │
    ▼
┌─────────────┐
│ 文件验证     │ - 文件类型检查
│             │ - 大小限制（50MB）
│             │ - 病毒扫描（可选）
└─────────────┘
    │
    ▼
┌─────────────┐
│ 文档解析     │ - PDF: PyMuPDF
│             │ - Word: python-docx
│             │ - Excel: openpyxl
│             │ - Markdown: markdown
│             │
│ ★ 多模态提取 │ - 图像提取（含位置）
│             │ - 表格识别与提取
│             │ - OCR识别（扫描件）
└─────────────┘
    │
    ▼
┌─────────────┐
│ 数据清洗     │ - 去除页眉页脚
│             │ - 去除特殊字符
│             │ - 格式标准化
└─────────────┘
    │
    ▼
┌─────────────┐
│ 文档分块     │ 策略：
│             │ - 固定大小: 512 tokens
│             │ - 语义分块: 基于句子边界
│             │ - 结构化: 按章节/标题
│             │
│ ★ 多模态策略 │ - multimodal: 综合策略
│             │ - table_first: 表格优先
│             │ - image_text: 图像-文本关联
└─────────────┘
    │
    ▼
┌─────────────┐
│ 向量化       │ - BGE-M3模型
│             │ - 1024维向量
│             │ - 批量处理
└─────────────┘
    │
    ├─────────────┐
    │             │
    ▼             ▼
┌─────────┐ ┌─────────┐
│ Milvus  │ │Meilisearch│
│ 向量插入 │ │ 索引构建  │
└─────────┘ └─────────┘
    │             │
    └─────────────┘
            │
            ▼
      写入PostgreSQL
```

### 2. 企业微信Bot集成

#### Webhook处理流程

```
用户发送消息
    │
    ▼
┌─────────────┐
│ 签名验证     │ - 验证msg_signature
│             │ - 验证timestamp
│             │ - 验证nonce
└─────────────┘
    │
    ▼
┌─────────────┐
│ 消息解密     │ - 使用EncodingAESKey
│             │ - 解密XML消息
└─────────────┘
    │
    ▼
┌─────────────┐
│ 用户身份验证  │ - 根据UserId查询
│             │ - 检查绑定状态
└─────────────┘
    │
    ▼
┌─────────────┐
│ 调用RAG     │ - 构建查询请求
│ Pipeline     │ - 获取答案+来源
└─────────────┘
    │
    ▼
┌─────────────┐
│ 消息格式化   │ - Markdown格式
│             │ - 引用卡片
│             │ - 建议问题
└─────────────┘
    │
    ▼
┌─────────────┐
│ 消息加密     │ - 使用EncodingAESKey
└─────────────┘
    │
    ▼
      返回给用户
```

#### 消息类型支持

| 消息类型 | 状态 | 说明 |
|---------|------|------|
| 文本消息 | ✅ 已支持 | 核心功能 |
| 图片消息 | 🔜 计划中 | OCR识别后查询 |
| 语音消息 | 🔜 计划中 | ASR转文字 |
| 文件消息 | 🔜 计划中 | 文档解析查询 |

### 3. 流式响应实现（SSE）

```python
async def stream_chat_response(query: str) -> AsyncGenerator[str, None]:
    """流式输出聊天响应"""

    async def generate():
        # 调用vLLM的OpenAI兼容API
        async for chunk in vllm_client.stream(
            messages=[{
                "role": "user",
                "content": query
            }],
            stream=True
        ):
            yield chunk.choices[0].delta.content or ""

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )
```

### 4. 缓存策略

```python
# Redis缓存键设计
CACHE_KEYS = {
    "query_result": "rag:query:{query_hash}:{user_id}",
    "document": "doc:{document_id}",
    "user_session": "session:{session_id}",
    "rate_limit": "rate:{user_id}:{endpoint}",
}

# 缓存过期时间
CACHE_TTL = {
    "query_result": 3600,      # 查询结果: 1小时
    "document": 86400,        # 文档: 1天
    "user_session": 7200,      # 会话: 2小时
    "rate_limit": 60,          # 限流: 1分钟
}
```

### 5. 权限控制（RBAC）

```python
# 权限定义
PERMISSIONS = {
    "document:read": "查看文档",
    "document:write": "编辑文档",
    "document:delete": "删除文档",
    "document:publish": "发布文档",
    "user:manage": "管理用户",
    "admin:dashboard": "访问管理后台",
}

# 角色定义
ROLES = {
    "employee": ["document:read"],
    "hr": ["document:read", "document:write", "document:publish"],
    "admin": ["*"],  # 所有权限
}

# 权限检查装饰器
def require_permission(permission: str):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            user = get_current_user()
            if not has_permission(user, permission):
                raise HTTPException(403, "权限不足")
            return await func(*args, **kwargs)
        return wrapper
    return decorator
```

---

## 快速开始

### 前置要求

| 组件 | 要求 |
|------|------|
| Python | 3.11+ |
| Node.js | 18+ |
| Docker | 20.10+ |
| Docker Compose | 2.20+ |
| GPU（可选） | NVIDIA GPU，24GB+ VRAM |
| 系统内存 | 32GB+ (推荐) |
| 磁盘空间 | 100GB+ |

### 方式一：快速启动（推荐）

#### 1. 克隆项目

```bash
git clone https://github.com/BGMer7/EnterpriseKB.git
cd EnterpriseKB
```

#### 2. 使用演示模式启动

**仅启动简化后端（无需外部服务）：**

```bash
# 后端
cd backend
pip install fastapi uvicorn pydantic pydantic-settings python-dotenv
python3 -m uvicorn app.main_simple:app --host 0.0.0.0 --port 8000

# 前端（新终端）
cd frontend
npm install
npm run dev
```

访问：http://localhost:3000

### 方式二：完整部署（Docker）

#### 1. 配置环境变量

```bash
cp deployment/.env.example deployment/.env
# 编辑 .env 文件，填入配置
```

**必填配置：**

```env
# 数据库
POSTGRES_USER=admin
POSTGRES_PASSWORD=your_secure_password
POSTGRES_DB=enterprisekb

# Redis
REDIS_PASSWORD=your_redis_password

# Milvus
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=minioadmin
```

**可选配置（企业微信）：**

```env
# 企业微信
WECHAT_CORP_ID=your_corp_id
WECHAT_APP_ID=your_app_id
WECHAT_APP_SECRET=your_app_secret
WECHAT_ENCODING_AES_KEY=your_aes_key
WECHAT_TOKEN=your_token
```

**可选配置（LLM）：**

```env
# vLLM
LLM_MODEL_NAME=Qwen/Qwen2.5-14B-Instruct-AWQ
VLLM_TENSOR_PARALLEL_SIZE=2
VLLM_GPU_MEMORY_UTILIZATION=0.9
```

#### 2. 启动所有服务

```bash
cd deployment
docker-compose up -d
```

这将启动以下服务：

| 服务 | 端口 | 说明 |
|------|--------|------|
| Nginx | 80/443 | 网关，SSL |
| Frontend | 3000 | Next.js |
| Backend | 8000 | FastAPI |
| PostgreSQL | 5432 | 数据库 |
| Redis | 6379 | 缓存 |
| Milvus | 19530 | 向量库 |
| Meilisearch | 7700 | 搜索引擎 |
| MinIO | 9000/9001 | 对象存储 |
| RabbitMQ | 5672/15672 | 消息队列 |
| vLLM | 8001 | LLM推理 |

#### 3. 初始化数据库

```bash
cd backend
pip install -r requirements.txt
alembic upgrade head
python scripts/init_db.py
```

#### 4. 访问应用

| 功能 | URL |
|------|------|
| Web应用 | http://localhost |
| API文档 | http://localhost/api/docs |
| MinIO控制台 | http://localhost:9001 |
| RabbitMQ管理 | http://localhost:15672 |

**默认管理员账号：**
- 用户名：`admin`
- 密码：`admin123`

⚠️ **生产环境请立即修改默认密码！**

### 方式三：分步部署（开发调试）

#### 后端

```bash
cd backend

# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env

# 启动数据库（Docker）
docker run -d --name postgres \
  -e POSTGRES_PASSWORD=password \
  -p 5432:5432 \
  postgres:16

# 运行迁移
alembic upgrade head

# 启动服务
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### 前端

```bash
cd frontend

# 安装依赖
npm install

# 配置环境变量
cp .env.local.example .env.local
# 编辑 .env.local

# 启动开发服务器
npm run dev
```

---

## 开发指南

### 后端开发

#### 项目结构

```
backend/
├── app/
│   ├── api/v1/          # API路由
│   │   ├── auth.py       # 认证接口
│   │   ├── chat.py       # 对话接口
│   │   ├── documents.py  # 文档管理
│   │   ├── qa_pairs.py   # QA对管理
│   │   ├── users.py      # 用户管理
│   │   └── admin.py      # 管理接口
│   │
│   ├── core/             # 核心模块
│   │   ├── security.py   # JWT, 加密
│   │   ├── permissions.py # 权限检查
│   │   └── constants.py  # 常量定义
│   │
│   ├── models/           # SQLAlchemy模型
│   │   ├── user.py
│   │   ├── document.py
│   │   └── ...
│   │
│   ├── schemas/          # Pydantic Schema
│   │   ├── chat.py
│   │   └── ...
│   │
│   ├── rag/              # RAG核心
│   │   ├── pipeline.py       # 主流程
│   │   ├── retriever/
│   │   │   ├── vector_retriever.py
│   │   │   ├── bm25_retriever.py
│   │   │   └── hybrid_retriever.py
│   │   ├── reranker/
│   │   │   └── bge_reranker.py
│   │   ├── generator/
│   │   │   ├── llm_client.py
│   │   │   └── prompt_builder.py
│   │   ├── postprocessor/
│   │   │   ├── citation.py
│   │   │   └── hallucination_check.py
│   │   └── embedding.py
│   │
│   ├── processors/       # 文档处理
│   │   ├── parser.py     # 文档解析（含多模态）
│   │   ├── chunker.py    # 文档分块
│   │   ├── multimodal_chunker.py  # 多模态分块
│   │   ├── cleaner.py    # 数据清洗
│   │   └── embedder.py   # 向量化
│   │
│   ├── integrations/     # 外部集成
│   │   ├── milvus_client.py
│   │   ├── search_engine.py
│   │   ├── llm_server.py
│   │   ├── minio_client.py
│   │   └── wechat/
│   │       ├── bot.py
│   │       ├── auth.py
│   │       └── message.py
│   │
│   ├── services/         # 业务服务层
│   │   ├── auth_service.py
│   │   ├── chat_service.py
│   │   ├── document_service.py
│   │   └── ...
│   │
│   ├── db/               # 数据库
│   │   ├── session.py
│   │   └── init_db.py
│   │
│   ├── tasks/            # 异步任务
│   │   ├── celery_app.py
│   │   └── document_tasks.py
│   │
│   └── main.py           # 应用入口
│
├── alembic/           # 数据库迁移
├── tests/              # 测试
├── scripts/            # 工具脚本
├── requirements/        # 依赖管理
└── Dockerfile
```

#### 添加新API端点

```python
# app/api/v1/new_feature.py
from fastapi import APIRouter, Depends
from app.core.security import get_current_user

router = APIRouter()

@router.get("/items")
async def list_items(
    skip: int = 0,
    limit: int = 100,
    current_user = Depends(get_current_user)
):
    """获取项目列表"""
    items = await get_items(skip=skip, limit=limit)
    return items

# app/main.py
from app.api.v1.new_feature import router as new_feature_router
app.include_router(new_feature_router, prefix="/api/v1", tags=["new_feature"])
```

#### 数据库迁移

```bash
# 创建新迁移
alembic revision --autogenerate -m "添加用户头像字段"

# 查看迁移SQL
alembic upgrade head --sql

# 应用迁移
alembic upgrade head

# 回滚
alembic downgrade -1
```

#### 运行测试

```bash
# 单元测试
pytest tests/unit/

# 集成测试
pytest tests/integration/

# 测试覆盖率
pytest --cov=app tests/
```

### 前端开发

#### 项目结构

```
frontend/
├── app/                 # Next.js App Router
│   ├── (chat)/          # 对话界面组
│   │   ├── layout.tsx
│   │   ├── page.tsx
│   │   └── history/[id]/page.tsx
│   │
│   ├── (admin)/         # 管理后台组
│   │   ├── layout.tsx
│   │   ├── dashboard/page.tsx
│   │   ├── documents/page.tsx
│   │   └── ...
│   │
│   ├── auth/            # 认证页面
│   │   ├── login/page.tsx
│   │   └── callback/page.tsx
│   │
│   ├── api/             # API路由（服务端）
│   │   └── chat/stream/route.ts
│   │
│   ├── layout.tsx         # 根布局
│   ├── page.tsx          # 首页
│   └── globals.css        # 全局样式
│
├── components/         # 组件
│   ├── chat/            # 对话组件
│   │   ├── ChatContainer.tsx
│   │   ├── MessageBubble.tsx
│   │   ├── CitationCard.tsx
│   │   └── SuggestionChips.tsx
│   │
│   ├── admin/           # 管理组件
│   │   ├── Sidebar.tsx
│   │   ├── DocumentTable.tsx
│   │   └── ...
│   │
│   └── ui/              # shadcn/ui组件
│
├── lib/               # 工具库
│   ├── api.ts           # API客户端
│   ├── auth.ts          # 认证工具
│   └── utils.ts         # 工具函数
│
├── hooks/             # 自定义Hooks
│   ├── useChat.ts       # 对话Hook
│   └── useAuth.ts       # 认证Hook
│
├── stores/            # Zustand状态
│   ├── chatStore.ts    # 对话状态
│   └── authStore.ts    # 认证状态
│
└── types/             # TypeScript类型
```

#### 添加新页面

```typescript
// app/(admin)/settings/page.tsx
export default function SettingsPage() {
  return (
    <div>
      <h1>系统设置</h1>
      {/* ... */}
    </div>
  );
}
```

#### 添加新组件

```typescript
// components/admin/SettingsForm.tsx
"use client";

export function SettingsForm() {
  // ...
  return (
    <form>
      {/* ... */}
    </form>
  );
}
```

#### 使用shadcn/ui添加新组件

```bash
# 添加Button组件
npx shadcn-ui@latest add button

# 添加Dialog组件
npx shadcn-ui@latest add dialog

# 添加Table组件
npx shadcn-ui@latest add table
```

---

## 部署指南

### 生产环境部署清单

#### 1. 安全加固

- [ ] 修改所有默认密码
- [ ] 配置HTTPS（SSL/TLS证书）
- [ ] 启用防火墙，仅开放必要端口
- [ ] 配置fail2ban防暴力破解
- [ ] 定期更新系统和依赖
- [ ] 配置日志审计

#### 2. 性能优化

| 优化项 | 配置 |
|--------|------|
| **数据库** | 连接池、索引优化、查询缓存 |
| **Redis** | 持久化配置、内存限制 |
| **Milvus** | 索引参数调优（M、efConstruction） |
| **vLLM** | GPU内存利用率、批量大小 |
| **Nginx** | Gzip压缩、缓存配置、限流 |

#### 3. 高可用架构

```
                ┌─────────────┐
                │   用户入口   │
                └─────────────┘
                        │
                        ▼
┌─────────────────────────────────────┐
│        Nginx + Keepalived          │
│        (负载均衡 + 高可用)            │
└─────────────────────────────────────┘
        │               │
        ▼               ▼
┌─────────────┐ ┌─────────────┐
│  后端节点1   │ │  后端节点2   │
└─────────────┘ └─────────────┘
        │               │
        └───────────────┴───────────────┐
                        │
                        ▼
              ┌──────────────────────┐
              │   共享存储集群      │
              │ (PostgreSQL + Redis)   │
              └──────────────────────┘
```

#### 4. 监控告警

推荐监控工具：

| 工具 | 用途 |
|------|------|
| Prometheus | 指标收集 |
| Grafana | 可视化看板 |
| Loki | 日志聚合 |
| Alertmanager | 告警通知 |

关键监控指标：

```
- API响应时间 (P50, P95, P99)
- QPS (每秒查询数)
- 错误率 (4xx, 5xx)
- 数据库连接数
- CPU/内存/磁盘使用率
- GPU显存使用率
- 缓存命中率
```

#### 5. 备份策略

| 数据 | 备份方式 | 频率 | 保留周期 |
|------|----------|--------|----------|
| PostgreSQL | pg_dump | 每天 | 30天 |
| Milvus | 数据导出 | 每天 | 7天 |
| MinIO | 对象同步 | 每小时 | 30天 |
| Redis | RDB快照 | 每天 | 7天 |

### 云服务集成

如需使用云服务替代自建组件：

| 组件 | 云服务选项 |
|------|-----------|
| PostgreSQL | 阿里云RDS、腾讯云PostgreSQL |
| 对象存储 | 阿里云OSS、腾讯云COS |
| Redis | 阿里云Redis、腾讯云Redis |
| LLM | 通义千问、DeepSeek、智谱AI |

---

## API文档

### 核心接口

#### 对话查询

```http
POST /api/v1/chat/query
Content-Type: application/json

{
  "query": "产假有多少天？"
}

Response 200 OK:
{
  "answer": "根据《请假管理办法》，产假98天...",
  "sources": [
    {
      "document_id": "doc001",
      "document_title": "请假管理制度",
      "section": "第四章",
      "content_preview": "产假98天+15天难产假..."
    }
  ],
  "suggested_questions": [
    "病假有多少天？",
    "婚假怎么算？",
    "陪产假多少天？"
  ]
}
```

#### 流式响应（SSE）

```http
POST /api/v1/chat/stream
Accept: text/event-stream

Response:
data: {"id": "1", "role": "assistant", "content": "根据"}
data: {"id": "1", "role": "assistant", "content": "《请假管理"}
data: {"id": "1", "role": "assistant", "content": "办法》"}
...
data: [DONE]
```

#### 文档上传

```http
POST /api/v1/documents/upload
Content-Type: multipart/form-data

file: <binary>
title: "员工请假制度"
department_id: "dept-001"
is_public: false

Response 201 Created:
{
  "id": "doc-001",
  "status": "processing",
  "created_at": "2024-01-15T10:00:00Z"
}
```

### 完整API文档

启动服务后访问：`http://your-host/api/docs`

---

## 常见问题

### Q1: 如何更换LLM模型？

编辑 `backend/.env`：

```env
# 修改模型名称
LLM_MODEL_NAME=Qwen/Qwen2.5-7B-Instruct-AWQ

# 或使用本地模型
LLM_MODEL_NAME=/path/to/your/model
```

重启后端服务即可。

### Q2: Milvus连接失败？

检查：

1. Docker容器是否运行：`docker ps | grep milvus`
2. 检查日志：`docker logs milvus-standalone`
3. 确认端口：`netstat -an | grep 19530`
4. 检查配置：`deployment/.env` 中的 `MILVUS_HOST`

### Q3: 如何增加文档上传大小限制？

编辑 `backend/app/config.py`：

```python
class Settings(BaseSettings):
    MAX_FILE_SIZE: int = 100 * 1024 * 1024  # 100MB
```

### Q4: 企业微信配置后无法登录？

检查配置：

```python
# backend/app/integrations/wechat/bot.py
def verify_webhook(...):
    # 确认token和encoding_aes_key正确
    # 确认corp_id匹配
```

使用企业微信验证工具：https://work.weixin.qq.com/debug

### Q5: 如何查看当前使用的模型？

```bash
curl http://localhost:8000/health

Response:
{
  "services": {
    "llm": "Qwen/Qwen2.5-14B-Instruct-AWQ",
    "vector_db": "Milvus 2.3.3",
    ...
  }
}
```

### Q6: 内存不足如何运行？

1. 使用量化模型（AWQ 4-bit）
2. 减小batch size
3. 使用小模型（7B替代14B）
4. 使用云API替代本地推理

---

## 贡献指南

欢迎贡献代码、报告问题或提出改进建议！

### 开发流程

1. Fork本仓库
2. 创建特性分支：`git checkout -b feature/amazing-feature`
3. 提交更改：`git commit -m "Add amazing feature"`
4. 推送分支：`git push origin feature/amazing-feature`
5. 创建Pull Request

### 代码规范

- Python遵循PEP 8
- TypeScript遵循ESLint配置
- 提交信息使用中文，清晰描述变更
- 添加必要的测试和文档

### 报告问题

使用GitHub Issues报告问题，请包含：
- 环境信息（OS、Python/Node版本）
- 错误信息
- 复现步骤

---

## 许可证

MIT License - 详见 [LICENSE](LICENSE) 文件

---

## 联系方式

- **Issues**: https://github.com/BGMer7/EnterpriseKB/issues
- **Email**: [your-email@example.com]

---

## 致谢

- [FastAPI](https://fastapi.tiangolo.com/) - 现代Python Web框架
- [Next.js](https://nextjs.org/) - React框架
- [Milvus](https://milvus.io/) - 向量数据库
- [vLLM](https://github.com/vllm-project/vllm) - LLM推理框架
- [Qwen](https://huggingface.co/Qwen) - 开源大语言模型

---

**EnterpriseKB** - 让企业制度查询更智能、更高效！
