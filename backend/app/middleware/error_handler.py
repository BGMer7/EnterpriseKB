"""
全局错误处理中间件
统一处理各种异常并返回格式化的错误响应
"""
import logging
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)


class AppError(Exception):
    """应用基础异常类"""

    def __init__(self, message: str, code: str = "APP_ERROR", status_code: int = 500):
        self.message = message
        self.code = code
        self.status_code = status_code
        super().__init__(self.message)


class ValidationError(AppError):
    """数据验证错误"""

    def __init__(self, message: str = "数据验证失败"):
        super().__init__(message, code="VALIDATION_ERROR", status_code=400)


class NotFoundError(AppError):
    """资源未找到错误"""

    def __init__(self, message: str = "资源不存在"):
        super().__init__(message, code="NOT_FOUND", status_code=404)


class PermissionError(AppError):
    """权限错误"""

    def __init__(self, message: str = "权限不足"):
        super().__init__(message, code="PERMISSION_DENIED", status_code=403)


class AuthenticationError(AppError):
    """认证错误"""

    def __init__(self, message: str = "认证失败"):
        super().__init__(message, code="AUTHENTICATION_FAILED", status_code=401)


class BusinessError(AppError):
    """业务逻辑错误"""

    def __init__(self, message: str = "操作失败"):
        super().__init__(message, code="BUSINESS_ERROR", status_code=400)


class ExternalServiceError(AppError):
    """外部服务错误"""

    def __init__(self, service: str, message: str = "外部服务调用失败"):
        super().__init__(
            f"[{service}] {message}",
            code="EXTERNAL_SERVICE_ERROR",
            status_code=502
        )


class RAGError(AppError):
    """RAG Pipeline错误"""

    def __init__(self, message: str = "RAG处理失败"):
        super().__init__(
            message,
            code="RAG_ERROR",
            status_code=500
        )


def add_exception_handlers(app: FastAPI) -> None:
    """添加全局异常处理器"""

    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError):
        """处理应用自定义错误"""
        logger.warning(
            f"AppError: {exc.code} - {exc.message} | "
            f"{request.method} {request.url.path}"
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "error": {
                    "code": exc.code,
                    "message": exc.message
                }
            }
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError):
        """处理请求验证错误"""
        errors = []
        for error in exc.errors():
            field = ".".join(str(loc) for loc in error["loc"][1:])  # 跳过'body'
            errors.append({
                "field": field,
                "message": error["msg"],
                "type": error["type"]
            })

        logger.warning(
            f"ValidationError: {errors} | "
            f"{request.method} {request.url.path}"
        )

        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "success": False,
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "请求参数验证失败",
                    "details": errors
                }
            }
        )

    @app.exception_handler(ValidationError)
    async def pydantic_validation_error_handler(request: Request, exc: ValidationError):
        """处理Pydantic验证错误"""
        errors = exc.errors()

        logger.warning(
            f"PydanticValidationError: {errors} | "
            f"{request.method} {request.url.path}"
        )

        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "success": False,
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "数据验证失败",
                    "details": errors
                }
            }
        )

    # @app.exception_handler(SQLAlchemyError)
    # async def database_error_handler(request: Request, exc: SQLAlchemyError):
    #     """处理数据库错误"""
    #     logger.error(
    #         f"DatabaseError: {str(exc)} | "
    #         f"{request.method} {request.url.path}",
    #         exc_info=True
    #     )
    #
    #     return JSONResponse(
    #         status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    #         content={
    #             "success": False,
    #             "error": {
    #                 "code": "DATABASE_ERROR",
    #                 "message": "数据库操作失败"
    #             }
    #         }
    #     )

    @app.exception_handler(Exception)
    async def general_error_handler(request: Request, exc: Exception):
        """处理所有未捕获的异常"""
        logger.error(
            f"UnhandledException: {str(exc)} | "
            f"{request.method} {request.url.path}",
            exc_info=True
        )

        # 总是显示详细错误信息用于调试
        import traceback
        error_message = f"{str(exc)}\n{traceback.format_exc()}"

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "success": False,
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": error_message
                }
            }
        )
