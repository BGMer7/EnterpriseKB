"""
FastAPI依赖注入工具（简化版，不依赖数据库）
"""


# ===== 用户认证依赖 =====
async def get_current_user():
    """
    获取当前登录用户（简化版，不依赖数据库）
    """
    class MockUser:
        def __init__(self):
            self.id = "test-user-id"
            self.wechat_id = "test_user"
            self.name = "测试用户"
            self.email = "test@example.com"
            self.is_active = True
            self.department_id = None
            self.roles = []

        def has_role(self, role_name: str):
            return True

        def has_permission(self, permission: str):
            return True

    return MockUser()


# 导出 MockUser 类供其他地方使用
MockUser = type('MockUser', (), {
    'id': 'test-user-id',
    'wechat_id': 'test_user',
    'name': '测试用户',
    'email': 'test@example.com',
    'is_active': True,
    'department_id': None,
    'roles': [],
    'has_role': lambda self, x: True,
    'has_permission': lambda self, x: True
})


async def get_current_active_user(current_user = None):
    """获取当前活跃用户"""
    return current_user or await get_current_user()


def require_permission(permission: str):
    """要求特定权限的依赖"""
    async def permission_checker(current_user=None) -> bool:
        return True
    return permission_checker


async def require_admin(current_user=None):
    """要求管理员权限"""
    return current_user or await get_current_user()


# ===== Milvus依赖 =====
async def get_milvus_client():
    """获取Milvus客户端"""
    from app.integrations.milvus_client import milvus_client
    return milvus_client


# ===== Meilisearch依赖 =====
async def get_meilisearch_client():
    """获取Meilisearch客户端"""
    from app.integrations.search_engine import meilisearch_client
    return meilisearch_client


# ===== LLM依赖 =====
async def get_llm_client():
    """获取LLM客户端"""
    from app.integrations.llm_server import llm_client
    return llm_client


# ===== RAG Pipeline依赖 =====
async def get_rag_pipeline():
    """获取RAG Pipeline实例"""
    from app.rag.pipeline import RAGPipeline
    from app.integrations.milvus_client import milvus_client
    from app.integrations.search_engine import meilisearch_client
    from app.integrations.llm_server import llm_client

    return RAGPipeline(
        vector_client=milvus_client,
        search_client=meilisearch_client,
        llm_client=llm_client
    )
