"""
企业微信Bot客户端
处理消息接收、发送、Webhook验证
"""
import logging
import xml.etree.ElementTree as ET
from typing import Dict, Any, List

from fastapi import Request

from app.core.security import verify_wechat_signature
from app.services.chat_service import get_chat_service
from app.models.user import get_user_service

logger = logging.getLogger(__name__)


class WeChatBot:
    """企业微信Bot客户端"""

    def __init__(self):
        self.token = None
        self._chat_service = None

    @property
    def chat_service(self):
        """获取对话服务（懒加载）"""
        if self._chat_service is None:
            self._chat_service = get_chat_service()
        return self._chat_service

    async def handle_message(
        self,
        user: Dict[str, Any],
        message_type: str,
        content: str,
        create_time: int
    ) -> str:
        """
        处理用户消息

        Args:
            user: 用户信息
            message_type: 消息类型
            content: 消息内容
            create_time: 消息创建时间

        Returns:
            str: 回复消息
        """
        user_id = user.get("UserId")
        logger.info(f"Received message from {user_id}: {message_type} - {content}")

        # 文本消息
        if message_type == "text":
            try:
                # 获取用户对象
                user_service = get_user_service()
                db = await user_service.get_db_session()
                user_obj = await user_service.get_by_wechat_id(db, user_id)
                await db.close()

                if not user_obj:
                    return "请先绑定企业微信账号"

                # 调用RAG获取回答
                result = await self.chat_service.query(
                    db=db,
                    user=user_obj,
                    query=content,
                    conversation_id=None
                )

                # 格式化回复
                return self._format_markdown_response(
                    answer=result.answer,
                    sources=result.sources
                )

            except Exception as e:
                logger.error(f"Error processing message: {e}")
                return f"抱歉，处理您的问题时出错了：{str(e)}"

        # 图片消息（TODO: 支持OCR）
        elif message_type == "image":
            return "暂不支持图片查询，请使用文字描述您的问题"

        # 其他消息类型
        else:
            return "暂不支持此类型消息"

    def _format_markdown_response(
        self,
        answer: str,
        sources: List[Dict[str, Any]]
    ) -> str:
        """
        格式化为Markdown回复

        Args:
            answer: 答案内容
            sources: 引用来源

        Returns:
            str: Markdown格式的回复
        """
        response = answer

        # 添加引用来源
        if sources:
            response += "\n\n---\n\n**参考来源：**\n\n"

            for idx, source in enumerate(sources, 1):
                title = source.get("document_title", "未知文档")
                section = source.get("section")
                preview = source.get("content_preview", "")[:50]

                response += f"{idx}. **{title}**\n"

                if section:
                    response += f"   章节：{section}\n"

                response += f"   内容：{preview}...\n"

        return response

    def verify_webhook(
        self,
        request: Request,
        msg_signature: str,
        msg_timestamp: str,
        msg_nonce: str,
        msg_encrypt: str
    ) -> bool:
        """
        验证Webhook

        Args:
            request: FastAPI请求
            msg_signature: 签名
            msg_timestamp: 时间戳
            msg_nonce: 随机字符串
            msg_encrypt: 加密消息

        Returns:
            bool: 验证是否通过
        """
        return verify_wechat_signature(
            signature=msg_signature,
            timestamp=msg_timestamp,
            nonce=msg_nonce,
            msg_encrypt=msg_encrypt
        )

    def parse_xml_message(self, xml_data: str) -> Dict[str, Any]:
        """
        解析XML消息

        Args:
            xml_data: XML数据

        Returns:
            Dict: 解析后的消息数据
        """
        root = ET.fromstring(xml_data)

        # 提取XML内容（解密后的）
        if root.tag == "xml":
            content = root.find("Content")
            if content is not None:
                xml_content = content.text
                msg_root = ET.fromstring(xml_content)

                msg_type = msg_root.find("MsgType")
                msg_type = msg_type.text if msg_type is not None else "unknown"

                # 文本消息
                if msg_type == "text":
                    content = msg_root.find("Content")
                    return {
                        "msg_type": "text",
                        "content": content.text if content is not None else "",
                        "msg_id": msg_root.find("MsgId").text if msg_root.find("MsgId") is not None else ""
                    }

                # 图片消息
                elif msg_type == "image":
                    media_id = msg_root.find("MediaId").text
                    return {
                        "msg_type": "image",
                        "media_id": media_id,
                        "msg_id": msg_root.find("MsgId").text if msg_root.find("MsgId") is not None else ""
                    }

        return {"msg_type": "unknown", "content": xml_data}

    def build_text_response(
        self,
        content: str
    ) -> str:
        """
        构建文本消息响应

        Args:
            content: 消息内容

        Returns:
            str: XML格式的消息响应
        """
        return f"""<xml>
<ToUserName><</ToUserName>
<FromUserName>EnterpriseKB</FromUserName>
<CreateTime>{int(__import__('time').time())}</CreateTime>
<MsgType>text</MsgType>
<Content>{content}</Content>
<MsgId>0</MsgId>
</xml>"""


# 全局Bot实例
wechat_bot = WeChatBot()


def get_wechat_bot() -> WeChatBot:
    """获取企业微信Bot单例"""
    return wechat_bot
