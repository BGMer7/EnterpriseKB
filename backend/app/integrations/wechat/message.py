"""
企业微信消息处理
构建和发送企业微信消息
"""
import logging
from typing import Optional, Dict, Any, List

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class WeChatMessage:
    """企业微信消息构建器"""

    @staticmethod
    def build_text_message(
        touser: str,
        content: str,
        msg_id: Optional[str] = None
    ) -> Dict[str, str]:
        """
        构建文本消息

        Args:
            touser: 接收用户UserID
            content: 消息内容
            msg_id: 消息ID

        Returns:
            Dict: 消息数据
        """
        import time

        message = {
            "touser": touser,
            "msgtype": "text",
            "text": {
                "content": content,
            },
            "agentid": settings.WECHAT_APP_ID,
            "msgid": msg_id
        }

        return message

    @staticmethod
    def build_markdown_message(
        touser: str,
        content: str,
        msg_id: Optional[str] = None
    ) -> Dict[str, str]:
        """
        构建Markdown消息

        Args:
            touser: 接收用户UserID
            content: Markdown格式内容
            msg_id: 消息ID

        Returns:
            Dict: 消息数据
        """
        message = {
            "touser": touser,
            "msgtype": "markdown",
            "markdown": {
                "content": content,
            },
            "agentid": settings.WECHAT_APP_ID,
            "msgid": msg_id
        }

        return message

    @staticmethod
    def build_news_message(
        articles: List[Dict[str, Any]],
        touser: Optional[str] = None
    ) -> Dict[str, str]:
        """
        构建图文消息

        Args:
            articles: 文章列表
            touser: 接收用户UserID

        Returns:
            Dict: 消息数据
        """
        message = {
            "touser": touser,
            "msgtype": "news",
            "news": {
                "articles": articles
            },
            "agentid": settings.WECHAT_APP_ID
        }

        return message

    @staticmethod
    def build_text_card_message(
        touser: str,
        title: str,
        description: str,
        url: Optional[str] = None,
        btn_text: str = "查看详情",
        btn_url: Optional[str] = None
    ) -> Dict[str, str]:
        """
        构建文本卡片消息

        Args:
            touser: 接收用户UserID
            title: 标题
            description: 描述
            url: 跳转链接
            btn_text: 按钮文本
            btn_url: 按钮链接

        Returns:
            Dict: 消息数据
        """
        message = {
            "touser": touser,
            "msgtype": "textcard",
            "textcard": {
                "title": title,
                "description": description,
                "url": url,
                "btntxt": btn_text,
                "btnurl": btn_url
            },
            "agentid": settings.WECHAT_APP_ID
        }

        return message

    @staticmethod
    async def send_message(
        message: Dict[str, str],
        access_token: str
    ) -> Dict[str, Any]:
        """
        发送企业微信消息

        Args:
            message: 消息数据
            access_token: 访问token

        Returns:
            Dict: 发送结果
        """
        url = f"https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={access_token}"

        async with httpx.AsyncClient(timeout=10) as client:
            try:
                response = await client.post(url, json=message)
                response.raise_for_status()
                result = response.json()

                if result.get("errcode") != 0:
                    error_msg = result.get("errmsg", "Unknown error")
                    logger.error(f"WeChat send message error: {error_msg}")
                    return {"success": False, "error": error_msg}

                return {"success": True, "data": result}

            except Exception as e:
                logger.error(f"Failed to send WeChat message: {e}")
                return {"success": False, "error": str(e)}

    @staticmethod
    def build_suggested_questions_card(
        query: str,
        questions: List[str]
    ) -> str:
        """
        构建预设问题卡片

        Args:
            query: 用户查询
            questions: 预设问题列表

        Returns:
            str: Markdown格式的问题卡片
        """
        markdown = f"""您可能还想了解：

{chr(10)}. {questions[0] if len(questions) > 0 else ''}"""

        for i, question in enumerate(questions[1:5], 2):
            if i < len(questions):
                markdown += f"{chr(10)}. {questions[i]}\n"

        return markdown

    @staticmethod
    def build_source_card(
        document_title: str,
        section: Optional[str],
        page_number: Optional[int],
        content: str
    ) -> str:
        """
        构建引用来源卡片

        Args:
            document_title: 文档标题
            section: 章节
            page_number: 页码
            content: 内容预览

        Returns:
            str: Markdown格式的来源卡片
        """
        markdown = f"**{document_title}**\n\n"

        if section:
            markdown += f"📍 章节：{section}\n"

        if page_number:
            markdown += f"📄 页码：第{page_number}页\n"

        markdown += f"📖 内容：\n{content}\n"

        return markdown
