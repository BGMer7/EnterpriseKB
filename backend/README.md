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
