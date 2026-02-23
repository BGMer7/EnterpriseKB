"""
应用常量定义
"""

# ===== 文档状态 =====
class DocumentStatus:
    """文档状态"""
    DRAFT = "draft"          # 草稿
    REVIEWING = "reviewing"  # 审核中
    PUBLISHED = "published"  # 已发布
    REJECTED = "rejected"    # 已拒绝


# ===== 消息角色 =====
class MessageRole:
    """消息角色"""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


# ===== 反馈类型 =====
class FeedbackType:
    """反馈类型"""
    HELPFUL = "helpful"
    NOT_HELPFUL = "not_helpful"
    INACCURATE = "inaccurate"


# ===== 用户状态 =====
class UserStatus:
    """用户状态"""
    ACTIVE = True
    INACTIVE = False


# ===== 权限定义 =====
class Permissions:
    """系统权限常量"""

    # 用户管理
    USER_VIEW = "user.view"
    USER_CREATE = "user.create"
    USER_UPDATE = "user.update"
    USER_DELETE = "user.delete"

    # 文档管理
    DOCUMENT_VIEW_ALL = "document.view_all"
    DOCUMENT_VIEW_OWN = "document.view_own"
    DOCUMENT_UPLOAD = "document.upload"
    DOCUMENT_EDIT = "document.edit"
    DOCUMENT_DELETE = "document.delete"
    DOCUMENT_AUDIT = "document.audit"

    # QA对管理
    QA_CREATE = "qa.create"
    QA_UPDATE = "qa.update"
    QA_DELETE = "qa.delete"
    QA_APPROVE = "qa.approve"

    # 对话管理
    CHAT_CREATE = "chat.create"
    CHAT_VIEW_OWN = "chat.view_own"
    CHAT_VIEW_ALL = "chat.view_all"

    # 系统管理
    SYSTEM_SETTINGS = "system.settings"
    SYSTEM_LOGS = "system.logs"
    SYSTEM_STATS = "system.stats"


# ===== 角色权限映射 =====
ROLE_PERMISSIONS = {
    "SUPER_ADMIN": [
        # 所有权限
        Permissions.USER_VIEW,
        Permissions.USER_CREATE,
        Permissions.USER_UPDATE,
        Permissions.USER_DELETE,
        Permissions.DOCUMENT_VIEW_ALL,
        Permissions.DOCUMENT_VIEW_OWN,
        Permissions.DOCUMENT_UPLOAD,
        Permissions.DOCUMENT_EDIT,
        Permissions.DOCUMENT_DELETE,
        Permissions.DOCUMENT_AUDIT,
        Permissions.QA_CREATE,
        Permissions.QA_UPDATE,
        Permissions.QA_DELETE,
        Permissions.QA_APPROVE,
        Permissions.CHAT_CREATE,
        Permissions.CHAT_VIEW_OWN,
        Permissions.CHAT_VIEW_ALL,
        Permissions.SYSTEM_SETTINGS,
        Permissions.SYSTEM_LOGS,
        Permissions.SYSTEM_STATS,
    ],
    "DEPT_ADMIN": [
        # 部门管理权限
        Permissions.USER_VIEW,
        Permissions.USER_UPDATE,
        Permissions.DOCUMENT_VIEW_ALL,
        Permissions.DOCUMENT_UPLOAD,
        Permissions.DOCUMENT_EDIT,
        Permissions.DOCUMENT_AUDIT,
        Permissions.QA_CREATE,
        Permissions.QA_UPDATE,
        Permissions.QA_APPROVE,
        Permissions.CHAT_CREATE,
        Permissions.CHAT_VIEW_ALL,
    ],
    "CONTENT_EDITOR": [
        # 内容编辑权限
        Permissions.DOCUMENT_VIEW_OWN,
        Permissions.DOCUMENT_UPLOAD,
        Permissions.DOCUMENT_EDIT,
        Permissions.QA_CREATE,
        Permissions.QA_UPDATE,
        Permissions.CHAT_CREATE,
    ],
    "CONTENT_AUDITOR": [
        # 内容审核权限
        Permissions.DOCUMENT_VIEW_ALL,
        Permissions.DOCUMENT_AUDIT,
        Permissions.QA_APPROVE,
        Permissions.CHAT_CREATE,
    ],
    "REGULAR_USER": [
        # 普通用户权限
        Permissions.DOCUMENT_VIEW_OWN,
        Permissions.CHAT_CREATE,
        Permissions.CHAT_VIEW_OWN,
    ],
}


# ===== 文档类型 =====
class DocumentType:
    """文档类型"""
    PDF = "pdf"
    DOCX = "docx"
    XLSX = "xlsx"
    TXT = "txt"
    MD = "md"


# ===== 审计日志动作 =====
class AuditAction:
    """审计动作"""
    LOGIN = "login"
    LOGOUT = "logout"
    DOCUMENT_UPLOAD = "document_upload"
    DOCUMENT_DELETE = "document_delete"
    DOCUMENT_UPDATE = "document_update"
    QUERY = "query"
    FEEDBACK = "feedback"
    USER_CREATE = "user_create"
    USER_UPDATE = "user_update"
    USER_DELETE = "user_delete"
    PERMISSION_CHANGE = "permission_change"
    SYSTEM_SETTING_CHANGE = "system_setting_change"


# ===== RAG相关 =====
class RAGConfig:
    """RAG配置常量"""
    DEFAULT_TOP_K = 30
    DEFAULT_RERANKER_TOP_K = 15
    DEFAULT_FUSION_K = 60
    MIN_RELEVANCE_SCORE = 0.7
    MAX_CONTEXT_TOKENS = 4000


# ===== 预设问题 =====
SUGGESTED_QUESTIONS = [
    "产假有多少天？",
    "差旅报销流程是什么？",
    "如何申请年假？",
    "办公用品怎么申领？",
    "社保公积金缴纳比例是多少？",
    "加班费如何计算？",
    "员工离职流程是什么？",
    "公司考勤制度是怎样的？",
]


# ===== 响应消息 =====
class ResponseMessage:
    """响应消息常量"""
    SUCCESS = "操作成功"
    UNAUTHORIZED = "未授权访问"
    FORBIDDEN = "权限不足"
    NOT_FOUND = "资源不存在"
    INVALID_PARAMS = "参数错误"
    SERVER_ERROR = "服务器错误"

    # 文档相关
    DOC_UPLOAD_SUCCESS = "文档上传成功"
    DOC_DELETE_SUCCESS = "文档删除成功"
    DOC_NOT_FOUND = "文档不存在"
    DOC_INVALID_TYPE = "不支持的文档类型"
    DOC_FILE_TOO_LARGE = "文件大小超出限制"
    DOC_PROCESSING = "文档处理中"

    # 对话相关
    CHAT_SUCCESS = "对话成功"
    CHAT_NOT_FOUND = "对话不存在"
    NO_RELEVANT_INFO = "根据现有文档，未找到相关信息"

    # 用户相关
    USER_NOT_FOUND = "用户不存在"
    USER_ALREADY_EXISTS = "用户已存在"
