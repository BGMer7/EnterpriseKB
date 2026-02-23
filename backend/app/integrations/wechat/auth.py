"""
企业微信认证相关
"""
import logging
from typing import Dict, Any, Optional

import httpx

from app.core.security import get_password_hash, create_access_token, decode_access_token
from app.db.session import get_db_session
from app.models.user import User
from app.config import settings

logger = logging.getLogger(__name__)


class WeChatAuth:
    """企业微信认证处理"""

    def __init__(self):
        self.app_id = settings.WECHAT_APP_ID
        self.app_secret = settings.WECHAT_APP_SECRET

    async def get_access_token(self) -> Optional[str]:
        """
        获取企业微信access_token（企业应用）

        Returns:
            Optional[str]: access_token
        """
        url = "https://qyapi.weixin.qq.com/cgi-bin/gettoken"

        params = {
            "corpid": settings.WECHAT_CORP_ID,
            "corpsecret": self.app_secret,
            "grant_type": "client_credential"
        }

        async with httpx.AsyncClient(timeout=10) as client:
            try:
                response = await client.get(url, params=params)
                response.raise_for_status()
                result = response.json()

                if result.get("errcode") != 0:
                    logger.error(f"Get WeChat access token error: {result.get('errmsg')}")
                    return None

                return result.get("access_token")

            except Exception as e:
                logger.error(f"Failed to get WeChat access token: {e}")
                return None

    async def get_jsapi_ticket(self) -> Optional[str]:
        """
        获取JSAPI Ticket

        Returns:
            Optional[str]: jsapi_ticket
        """
        access_token = await self.get_access_token()
        if not access_token:
            return None

        url = "https://qyapi.weixin.qq.com/cgi-bin/get_jsapi_ticket"

        params = {
            "type": "agent_config"
            "agentid": self.app_id,
            "access_token": access_token
        }

        async with httpx.AsyncClient(timeout=10) as client:
            try:
                response = await client.get(url, params=params)
                response.raise_for_status()
                result = response.json()

                if result.get("errcode") != 0:
                    logger.error(f"Get JSAPI ticket error: {result.get('errmsg')}")
                    return None

                return result.get("ticket")

            except Exception as e:
                logger.error(f"Failed to get JSAPI ticket: {e}")
                return None

    async def verify_user(
        self,
        code: str,
        state: str
    ) -> Optional[Dict[str, Any]]:
        """
        验证用户身份（企业微信OAuth）

        Args:
            code: 授权码
            state: 状态参数

        Returns:
            Optional[Dict]: 用户信息
        """
        access_token = await self.get_access_token()
        if not access_token:
            return None

        # 获取用户信息
        url = f"https://qyapi.weixin.qq.com/cgi-bin/user/getuserinfo?access_token={access_token}&agentid={self.app_id}"

        async with httpx.AsyncClient(timeout=10) as client:
            try:
                response = await client.get(url)
                response.raise_for_status()
                result = response.json()

                if result.get("errcode") != 0:
                    logger.error(f"Get userinfo error: {result.get('errmsg')}")
                    return None

                return {
                    "userid": result.get("userid"),
                    "name": result.get("name"),
                    "department": result.get("department"),
                    "position": result.get("position"),
                    "mobile": result.get("mobile"),
                    "email": result.get("email"),
                    "avatar": result.get("avatar"),
                }

            except Exception as e:
                logger.error(f"Failed to get userinfo: {e}")
                return None

    async def get_contact_info(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        获取通讯录成员信息

        Args:
            user_id: 企业微信UserID

        Returns:
            Optional[Dict]: 联系人信息
        """
        access_token = await self.get_access_token()
        if not access_token:
            return None

        url = f"https://qyapi.weixin.qq.com/cgi-bin/user/get?access_token={access_token}&userid={user_id}"

        async with httpx.AsyncClient(timeout=10) as client:
            try:
                response = await client.get(url)
                response.raise_for_status()
                result = response.json()

                if result.get("errcode") != 0:
                    logger.error(f"Get contact error: {result.get('errmsg')}")
                    return None

                return result

            except Exception as e:
                logger.error(f"Failed to get contact info: {e}")
                return None


# 全局认证实例
wechat_auth = WeChatAuth()


def get_wechat_auth() -> WeChatAuth:
    """获取企业微信认证单例"""
    return wechat_auth
