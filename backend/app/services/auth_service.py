"""
认证服务
实现企业微信SSO登录、JWT Token管理
"""
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    verify_wechat_signature,
    mask_email
)
from app.core.constants import Permissions
from app.db.session import get_db_session
from app.models.user import User, UserRole, Department
from app.models.role import Role
from app.schemas.user import LoginResponse, UserResponse
from app.config import settings

logger = logging.getLogger(__name__)


class AuthService:
    """认证服务"""

    async def login_with_wechat(
        self,
        db: AsyncSession,
        code: str
    ) -> LoginResponse:
        """
        企业微信授权码登录

        Args:
            db: 数据库会话
            code: 企业微信授权码

        Returns:
            LoginResponse: 登录响应
        """
        # 1. 使用code获取access_token
        access_token = await self._get_wechat_access_token(code)
        if not access_token:
            raise RuntimeError("Failed to get WeChat access token")

        # 2. 获取用户信息
        wechat_user = await self._get_wechat_user_info(access_token)
        if not wechat_user:
            raise RuntimeError("Failed to get WeChat user info")

        # 3. 查找或创建用户
        user = await self._get_or_create_user(db, wechat_user)

        # 4. 生成JWT Token
        access_token_jwt = create_access_token(
            subject=str(user.id),
            additional_claims={"name": user.name}
        )
        refresh_token_jwt = create_refresh_token(subject=str(user.id))

        # 5. 更新最后登录时间
        user.last_login_at = datetime.utcnow()
        await db.commit()
        await db.refresh(user)

        # 记录审计日志
        await self._log_audit(db, user, "login", {"wechat_user_id": wechat_user["userid"]})

        return LoginResponse(
            access_token=access_token_jwt,
            refresh_token=refresh_token_jwt,
            token_type="bearer",
            user=UserResponse.model_validate(user)
        )

    async def _get_wechat_access_token(self, code: str) -> Optional[str]:
        """
        使用授权码获取企业微信access_token
        """
        import httpx

        url = f"https://qyapi.weixin.qq.com/cgi-bin/gettoken?corpid={settings.WECHAT_CORP_ID}&corpsecret={settings.WECHAT_APP_SECRET}"

        async with httpx.AsyncClient(timeout=10) as client:
            try:
                response = await client.get(url)
                response.raise_for_status()
                data = response.json()

                if data.get("errcode") != 0:
                    error_msg = data.get("errmsg", "Unknown error")
                    logger.error(f"WeChat API error: {error_msg}")
                    return None

                return data.get("access_token")
            except Exception as e:
                logger.error(f"Failed to get WeChat access token: {e}")
                return None

    async def _get_wechat_user_info(self, access_token: str) -> Optional[Dict[str, Any]]:
        """
        获取企业微信用户信息
        """
        import httpx

        url = f"https://qyapi.weixin.qq.com/cgi-bin/auth/getuserinfo?access_token={access_token}"

        async with httpx.AsyncClient(timeout=10) as client:
            try:
                response = await client.get(url)
                response.raise_for_status()
                data = response.json()

                if data.get("errcode") != 0:
                    error_msg = data.get("errmsg", "Unknown error")
                    logger.error(f"WeChat API error: {error_msg}")
                    return None

                return data
            except Exception as e:
                logger.error(f"Failed to get WeChat user info: {e}")
                return None

    async def _get_or_create_user(
        self,
        db: AsyncSession,
        wechat_user: Dict[str, Any]
    ) -> User:
        """
        获取或创建用户

        Args:
            db: 数据库会话
            wechat_user: 企业微信用户信息

        Returns:
            User: 用户对象
        """
        wechat_id = wechat_user["userid"]
        name = wechat_user.get("name", "Unknown")

        # 查找现有用户
        result = await db.execute(
            select(User).where(User.wechat_id == wechat_id)
        )
        user = result.scalar_one_or_none()

        if user:
            # 更新用户信息
            if user.name != name:
                user.name = name
            # 用户被禁用
            if not user.is_active:
                user.is_active = True

            await db.commit()
            await db.refresh(user)
            return user

        # 创建新用户
        # 获取默认角色
        result = await db.execute(
            select(Role).where(Role.name == settings.DEFAULT_ROLE)
        )
        default_role = result.scalar_one_or_none()

        # 查找用户部门（根据部门名称匹配）
        department_id = await self._match_department_by_name(db, wechat_user.get("department"))

        user = User(
            wechat_id=wechat_id,
            name=name,
            email=mask_email(f"{wechat_id}@enterprise.com"),
            department_id=department_id,
            is_active=True,
            roles=[default_role] if default_role else []
        )

        db.add(user)
        await db.commit()
        await db.refresh(user)

        logger.info(f"Created new user: {name} ({wechat_id})")

        return user

    async def _match_department_by_name(
        self,
        db: AsyncSession,
        dept_name: Optional[str]
    ) -> Optional[str]:
        """
        根据部门名称匹配部门

        Args:
            db: 数据库会话
            dept_name: 部门名称

        Returns:
            Optional[str]: 匹配的部门ID
        """
        if not dept_name:
            return None

        # 模糊匹配部门名称
        result = await db.execute(
            select(Department).where(Department.name.ilike(f"%{dept_name}%"))
        )
        dept = result.scalar_one_or_none()

        return dept.id if dept else None

    async def refresh_tokens(
        self,
        db: AsyncSession,
        refresh_token: str
    ) -> Dict[str, str]:
        """
        刷新access_token

        Args:
            db: 数据库会话
            refresh_token: 刷新token

        Returns:
            Dict: 新的token
        """
        # 验证refresh_token
        payload = decode_refresh_token(refresh_token)
        user_id = payload.get("sub")
        if not user_id:
            raise ValueError("Invalid refresh token")

        # 查询用户
        result = await db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        if not user or not user.is_active:
            raise ValueError("User not found or inactive")

        # 生成新token
        new_access_token = create_access_token(subject=str(user.id))
        new_refresh_token = create_refresh_token(subject=str(user.id))

        return {
            "access_token": new_access_token,
            "refresh_token": new_refresh_token
        }

    async def _log_audit(
        self,
        db: AsyncSession,
        user: User,
        action: str,
        request_data: Optional[Dict] = None
    ):
        """
        记录审计日志

        Args:
            db: 数据库会话
            user: 用户对象
            action: 动作
            request_data: 请求数据
        """
        from app.models.audit_log import AuditLog

        audit_log = AuditLog(
            user_id=str(user.id),
            action=action,
            request_data=request_data or {}
        )

        db.add(audit_log)
        try:
            await db.commit()
        except Exception as e:
            logger.error(f"Failed to log audit: {e}")


# 全局认证服务实例
auth_service = AuthService()


def get_auth_service() -> AuthService:
    """获取认证服务单例"""
    return auth_service
