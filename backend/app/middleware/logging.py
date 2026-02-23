"""
日志中间件
记录所有API请求和响应
"""
import time
import logging
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("api")


class LoggingMiddleware(BaseHTTPMiddleware):
    """请求日志中间件"""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable
    ) -> Response:
        """
        处理请求并记录日志

        Args:
            request: HTTP请求
            call_next: 下一个中间件/处理器

        Returns:
            Response: HTTP响应
        """
        # 记录请求开始
        start_time = time.time()

        # 获取客户端信息
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "unknown")

        # 获取用户信息（如果已认证）
        user_id = "anonymous"
        auth_header = request.headers.get("authorization")
        if auth_header:
            try:
                from app.core.security import decode_access_token
                scheme, token = auth_header.split()
                if scheme.lower() == "bearer":
                    payload = decode_access_token(token)
                    user_id = payload.get("sub", "anonymous")
            except Exception:
                pass

        # 记录请求
        logger.info(
            f"Request: {request.method} {request.url.path} | "
            f"Client: {client_ip} | User: {user_id} | "
            f"UA: {user_agent[:50]}"
        )

        # 处理请求
        try:
            response = await call_next(request)

            # 记录响应
            process_time = time.time() - start_time
            logger.info(
                f"Response: {response.status_code} | "
                f"Time: {process_time:.3f}s | "
                f"{request.method} {request.url.path}"
            )

            # 添加处理时间到响应头
            response.headers["X-Process-Time"] = str(process_time)

            return response

        except Exception as e:
            # 记录错误
            process_time = time.time() - start_time
            logger.error(
                f"Error: {str(e)} | "
                f"Time: {process_time:.3f}s | "
                f"{request.method} {request.url.path}",
                exc_info=True
            )
            raise
