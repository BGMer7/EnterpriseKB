"""
Meilisearch全文搜索引擎客户端
支持Index管理、BM25搜索、中文分词
"""
from typing import List, Optional, Dict, Any
import json

import meilisearch

from app.config import settings


class MeilisearchClientWrapper:
    """
    Meilisearch客户端包装类
    """

    def __init__(
        self,
        url: str = settings.MEILISEARCH_URL,
        api_key: str = settings.MEILISEARCH_API_KEY or None,
        index_name: str = settings.MEILISEARCH_INDEX_NAME
    ):
        self.url = url
        self.api_key = api_key or None
        self.index_name = index_name
        self._client = None

    def connect(self) -> meilisearch.Client:
        """
        连接到Meilisearch服务器
        """
        if self._client is None:
            self._client = meilisearch.Client(
                url=self.url,
                api_key=self.api_key
            )
        return self._client

    @property
    def client(self) -> meilisearch.Client:
        """获取Meilisearch客户端"""
        if self._client is None:
            self.connect()
        return self._client

    def check_health(self) -> str:
        """
        检查Meilisearch健康状态，并自动创建Index
        """
        try:
            self.client.get_indexes()

            # 自动创建Index（如果不存在）
            try:
                self.client.get_index(self.index_name)
            except Exception:
                # Index不存在，创建它
                self.client.create_index(self.index_name, {"primaryKey": "chunk_id"})

            return "healthy"
        except Exception as e:
            return f"unhealthy: {str(e)}"

    # ===== Index管理 =====
    def create_index(self, overwrite: bool = False) -> bool:
        """
        创建Index

        Args:
            overwrite: 是否覆盖已存在的Index

        Returns:
            bool: 是否创建成功
        """
        client = self.client

        # 检查Index是否存在
        indexes = client.get_indexes()
        index_names = [index.uid for index in indexes["results"]]

        if self.index_name in index_names:
            if overwrite:
                client.delete_index(self.index_name)
            else:
                print(f"Index {self.index_name} already exists")
                return False

        # 创建Index
        client.create_index(self.index_name)

        # 配置Index
        self._configure_index()

        print(f"Index {self.index_name} created successfully")
        return True

    def _configure_index(self):
        """
        配置Index设置
        """
        index = self.client.index(self.index_name)

        # 设置可搜索字段
        index.update_searchable_attributes([
            "title",
            "content",
            "section"
        ])

        # 设置可过滤字段
        index.update_filterable_attributes([
            "document_id",
            "department_id",
            "is_public",
            "allowed_roles"
        ])

        # 设置可排序字段
        index.update_sortable_attributes([
            "created_at",
            "chunk_index"
        ])

        # 设置显示字段
        index.update_displayed_attributes([
            "chunk_id",
            "document_id",
            "content",
            "title",
            "department_id",
            "is_public",
            "allowed_roles",
            "page_number",
            "section",
            "chunk_index",
            "created_at"
        ])

        # 设置停用词
        index.update_stop_words([
            # 中文停用词
            "的", "了", "在", "是", "我", "有", "和", "就",
            "不", "人", "都", "一", "一个", "上", "也", "很",
            "到", "说", "要", "去", "你", "会", "着", "没有",
            "看", "好", "自己", "这",
            # 英文停用词
            "the", "and", "or", "but", "in", "on", "at", "to",
            "a", "an", "is", "are", "was", "were", "be", "been",
            "being", "have", "has", "had", "do", "does", "did"
        ])

        # 设置排序规则
        index.update_ranking_rules([
            "words",
            "typo",
            "proximity",
            "attribute",
            "sort",
            "exactness"
        ])

    def drop_index(self) -> bool:
        """
        删除Index

        Returns:
            bool: 是否删除成功
        """
        client = self.client

        try:
            client.delete_index(self.index_name)
            print(f"Index {self.index_name} dropped")
            return True
        except Exception as e:
            print(f"Failed to drop index: {e}")
            return False

    def get_index(self):
        """
        获取Index对象

        Returns:
            Index: Meilisearch Index对象
        """
        return self.client.index(self.index_name)

    # ===== 数据操作 =====
    def add_documents(
        self,
        documents: List[Dict[str, Any]]
    ) -> int:
        """
        添加文档到Index

        Args:
            documents: 文档列表
                {
                    "chunk_id": str,
                    "document_id": str,
                    "content": str,
                    "title": str,
                    "department_id": Optional[str],
                    "is_public": bool,
                    "allowed_roles": List[str],
                    "page_number": Optional[int],
                    "section": Optional[str],
                    "chunk_index": int,
                    "created_at": int,
                }

        Returns:
            int: 添加的文档数量
        """
        index = self.get_index()

        if not documents:
            return 0

        # 添加文档
        task = index.add_documents(documents)

        return len(documents)

    def delete_chunks(self, chunk_ids: List[str]) -> int:
        """
        删除文档块数据

        Args:
            chunk_ids: SQLite chunk ID列表

        Returns:
            int: 删除的数量
        """
        index = self.get_index()

        if not chunk_ids:
            return 0

        # 删除文档
        task = index.delete_documents(chunk_ids)

        return len(chunk_ids)

    def delete_by_document(self, document_id: str) -> int:
        """
        根据文档ID删除所有相关chunk

        Args:
            document_id: SQLite document ID

        Returns:
            int: 删除的数量
        """
        index = self.get_index()

        # 搜索获取要删除的文档ID
        results = index.search(
            "",
            {"filter": f'document_id = "{document_id}"', "limit": 10000}
        )

        if not results["hits"]:
            return 0

        chunk_ids = [hit["chunk_id"] for hit in results["hits"]]

        # 删除文档
        task = index.delete_documents(chunk_ids)

        return len(chunk_ids)

    # ===== 检索操作 =====
    def search(
        self,
        query: str,
        limit: int = 30,
        filter_expression: Optional[str] = None,
        output_fields: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        BM25全文检索

        Args:
            query: 查询文本
            limit: 返回结果数量
            filter_expression: 过滤表达式（用于权限控制）
            output_fields: 返回字段列表

        Returns:
            List[Dict]: 检索结果列表
        """
        index = self.get_index()

        # 设置输出字段
        if output_fields is None:
            output_fields = [
                "chunk_id", "document_id", "content", "title",
                "department_id", "is_public", "allowed_roles",
                "page_number", "section", "chunk_index"
            ]

        # 执行检索 - 直接传递参数
        results = index.search(
            query,
            {"limit": limit}
        )

        # 格式化结果
        formatted_results = []
        for hit in results["hits"]:
            # 获取BM25分数，新版Meilisearch返回格式可能不同
            ranking_score = hit.get("_rankingScore", hit.get("_ BM25_1.2.3", 1.0))
            # 如果没有分数，使用默认分数
            if ranking_score is None:
                ranking_score = 1.0
            # 转换BM25分数为相似度分数（越高越好）
            similarity_score = 1.0 - (min(float(ranking_score), 1000) / 1000) if ranking_score else 0.5

            formatted_results.append({
                "id": hit["chunk_id"],
                "score": similarity_score,
                "chunk_id": hit.get("chunk_id"),
                "document_id": hit.get("document_id"),
                "content": hit.get("content"),
                "title": hit.get("title"),
                "department_id": hit.get("department_id"),
                "is_public": hit.get("is_public"),
                "allowed_roles": hit.get("allowed_roles", []),
                "page_number": hit.get("page_number"),
                "section": hit.get("section"),
                "chunk_index": hit.get("chunk_index"),
            })

        return formatted_results

    def build_permission_filter(
        self,
        department_id: Optional[str],
        roles: List[str]
    ) -> str:
        """
        构建权限过滤表达式

        Args:
            department_id: 用户部门ID
            roles: 用户角色列表

        Returns:
            str: Meilisearch过滤表达式
        """
        conditions = []

        # 公开文档
        conditions.append("is_public = true")

        # 同部门文档
        if department_id:
            conditions.append(f'department_id = "{department_id}"')

        # 角色允许的文档
        for role in roles:
            conditions.append(f'allowed_roles = "{role}"')

        # 使用OR连接
        return " OR ".join(conditions)

    # ===== 批量操作 =====
    def update_documents(
        self,
        documents: List[Dict[str, Any]]
    ) -> int:
        """
        更新文档

        Args:
            documents: 文档列表

        Returns:
            int: 更新的文档数量
        """
        return self.add_documents(documents)  # Meilisearch自动根据chunk_id更新

    # ===== 统计信息 =====
    def get_index_stats(self) -> Dict[str, Any]:
        """
        获取Index统计信息

        Returns:
            Dict: 统计信息
        """
        index = self.get_index()

        try:
            stats = index.get_stats()

            return {
                "exists": True,
                "name": self.index_name,
                "count": stats.get("numberOfDocuments", 0),
            }
        except Exception as e:
            return {
                "exists": False,
                "count": 0,
                "error": str(e)
            }


# 全局Meilisearch客户端实例
meilisearch_client = MeilisearchClientWrapper()


def get_meilisearch_client() -> MeilisearchClientWrapper:
    """获取Meilisearch客户端单例"""
    return meilisearch_client
