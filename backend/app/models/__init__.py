"""数据模型模块初始化"""
# 必须先导入子类，再导入父类
from app.models.department import Department
from app.models.role import Role
from app.models.user_role import UserRole
from app.models.user import User
from app.models.document import Document
from app.models.chunk import Chunk
from app.models.chunk_qa_pair import ChunkQAPair
from app.models.qa_pair import QAPair
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.audit_log import AuditLog

__all__ = [
    "Department",
    "Role",
    "UserRole",
    "User",
    "Document",
    "Chunk",
    "ChunkQAPair",
    "QAPair",
    "Conversation",
    "Message",
    "AuditLog",
]
