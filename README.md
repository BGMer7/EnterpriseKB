# EnterpriseKB - 企业内部制度查询助手 (RAG Chatbot)

> 基于RAG技术的企业内部制度智能问答系统，为员工提供7x24小时制度查询服务

## 功能特性

### 核心功能
- **智能问答**：基于RAG技术，基于企业制度文档回答员工问题
- **引用溯源**：每次回答附带文档来源，支持点击查看原文
- **多轮对话**：支持上下文理解的多轮追问
- **预设问题**：热门问题快速入口
- **反馈机制**：用户可对回答进行评价，持续优化效果

### 后台管理
- **文档管理**：多格式文档上传、版本管理、审核流程
- **QA对管理**：自动生成QA对、人工审核维护
- **用户权限**：RBAC权限控制、部门隔离
- **数据看板**：问答统计、热门问题、运营分析

### 技术特点
- **防幻觉**：混合检索+权限过滤，确保答案准确
- **本地部署**：数据不出域，完全私有化
- **高可用**：支持百级并发，响应时间<5秒
- **企业微信**：Bot集成，扫码登录

## 技术架构

### 后端
- **框架**：FastAPI + Python 3.11
- **数据库**：PostgreSQL 16
- **向量数据库**：Milvus Standalone
- **全文搜索**：Meilisearch
- **LLM**：Qwen2.5-14B-Instruct + vLLM
- **Embedding**：BGE-M3
- **Reranker**：BGE-Reranker

### 前端
- **框架**：Next.js 14 + TypeScript
- **UI组件**：shadcn/ui + Tailwind CSS
- **状态管理**：Zustand

### 基础设施
- **缓存**：Redis 7
- **对象存储**：MinIO
- **消息队列**：RabbitMQ
- **部署**：Docker + Docker Compose

## 快速开始

### 前置要求

- Python 3.11+
- Node.js 18+
- Docker & Docker Compose
- NVIDIA GPU (24GB+ VRAM，可选，用于本地LLM)

### 1. 克隆项目

```bash
git clone <repository-url>
cd EnterpriseKB
```

### 2. 配置环境变量

```bash
cp .env.local.example .env
# 编辑 .env 文件，填入必要的配置
```

### 3. 启动所有服务

```bash
cd deployment
docker-compose up -d
```

这将启动：
- PostgreSQL
- Redis
- Milvus
- Meilisearch
- MinIO
- RabbitMQ
- Backend
- Frontend
- Nginx

### 4. 初始化数据库

```bash
cd backend
pip install -r requirements/dev.txt
python -m alembic upgrade head
python scripts/init_db.py
```

### 5. 访问应用

- Web界面：http://localhost
- API文档：http://localhost/api/docs
- MinIO控制台：http://localhost:9001
- RabbitMQ管理：http://localhost:15672

默认管理员账号：
- 用户名：admin
- 密码：admin123

## 项目结构

```
EnterpriseKB/
├── backend/               # 后端项目
│   ├── app/
│   │   ├── api/v1/       # API路由
│   │   ├── core/         # 核心模块（安全、权限）
│   │   ├── models/       # 数据模型
│   │   ├── schemas/      # Pydantic Schema
│   │   ├── rag/          # RAG核心
│   │   ├── processors/   # 文档处理
│   │   ├── integrations/ # 外部集成
│   │   ├── services/     # 业务服务
│   │   └── middleware/   # 中间件
│   ├── alembic/         # 数据库迁移
│   ├── requirements/     # 依赖管理
│   └── Dockerfile
├── frontend/            # 前端项目
│   ├── app/            # Next.js App Router
│   ├── components/     # 组件
│   ├── lib/            # 工具库
│   └── stores/         # 状态管理
└── deployment/         # 部署配置
    └── docker-compose.yml
```

## 开发指南

### 后端开发

```bash
cd backend
pip install -r requirements/dev.txt
python -m app.main
```

### 前端开发

```bash
cd frontend
npm install
npm run dev
```

### 数据库迁移

```bash
cd backend
alembic revision --autogenerate -m "描述"
alembic upgrade head
```

## 部署

### Docker部署

```bash
cd deployment
docker-compose up -d
```

### 生产环境建议

1. 使用HTTPS（配置SSL证书）
2. 修改默认密码和密钥
3. 配置监控和日志
4. 使用外部对象存储（如阿里云OSS）
5. 配置高可用架构

## 文档

- [API文档](docs/api.md)
- [架构文档](docs/architecture.md)
- [部署文档](docs/deployment.md)

## 贡献

欢迎提交Issue和Pull Request。

## 许可证

MIT License
