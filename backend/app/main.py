"""
EnterpriseKB - 企业内部制度查询助手
FastAPI应用入口
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import logging
import os

from app.config import settings
from app.db import session as db_session
from app.middleware.logging import LoggingMiddleware
from app.middleware.error_handler import add_exception_handlers

# 配置日志
logging.basicConfig(
    level=settings.LOG_LEVEL,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时初始化（跳过数据库）
    logger.info("Starting EnterpriseKB... (no DB)")

    yield

    # 关闭时清理
    logger.info("Shutting down EnterpriseKB...")


# 创建FastAPI应用
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="企业内部制度查询助手 - RAG Chatbot API",
    version=settings.VERSION,
    docs_url="/api/docs" if settings.SHOW_DOCS else None,
    redoc_url="/api/redoc" if settings.SHOW_DOCS else None,
    lifespan=lifespan,
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 添加自定义中间件
app.add_middleware(LoggingMiddleware)

# 添加异常处理器
add_exception_handlers(app)


# 健康检查
@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {"status": "healthy", "version": settings.VERSION}


# 根路径 - 返回测试页面
@app.get("/")
async def root():
    """根路径"""
    # 返回测试页面
    test_page_path = os.path.join(os.path.dirname(__file__), "static", "test.html")
    if os.path.exists(test_page_path):
        return FileResponse(test_page_path)
    return {
        "message": "EnterpriseKB API",
        "version": settings.VERSION,
        "docs": "/api/docs" if settings.SHOW_DOCS else None,
    }


# 导入路由 (仅保留 chat，其他禁用)
from app.api.v1 import chat

app.include_router(chat.router, prefix="/api/v1/chat", tags=["Chat"])


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        workers=1 if settings.DEBUG else settings.WORKERS,
    )
