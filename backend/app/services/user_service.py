"""
用户服务
实现用户CRUD、角色管理、部门管理
"""
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models.user import User, UserRole, Department
from app.models.role import Role
from app.schemas.user import UserResponse, DepartmentResponse, RoleResponse
from app.config import settings

logger = logging.getLogger(__name__)


class UserService:
    """用户服务"""

    async def get_by_id(
        self,
        db: AsyncSession,
        user_id: str
    ) -> Optional[User]:
        """
        根据ID获取用户

        Args:
            db: 数据库会话
            user_id: 用户ID

        Returns:
            Optional[User]: 用户对象
        """
        result = await db.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_by_wechat_id(
        self,
        db: AsyncSession,
        wechat_id: str
    ) -> Optional[User]:
        """
        根据企业微信ID获取用户

        Args:
            db: 数据库会话
            wechat_id: 企业微信ID

        Returns:
            Optional[User]: 用户对象
        """
        result = await db.execute(
            select(User).where(User.wechat_id == wechat_id)
        )
        return result.scalar_one_or_none()

    async def list_users(
        self,
        db: AsyncSession,
        page: int = 1,
        page_size: int = 20,
        department_id: Optional[str] = None,
        search: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        获取用户列表

        Args:
            db: 数据库会话
            page: 页码
            page_size: 每页数量
            department_id: 部门ID过滤
            search: 搜索关键词

        Returns:
            Dict: {users, total, page, page_size}
        """
        query = select(User).options(select(User).joinedload(User.roles))

        # 应用过滤
        if department_id:
            query = query.where(User.department_id == department_id)

        if search:
            search_pattern = f"%{search}%"
            query = query.where(User.name.ilike(search_pattern))

        # 计算总数
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        # 分页
        query = query.order_by(User.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await db.execute(query)
        users = result.scalars().all()

        return {
            "users": [UserResponse.model_validate(u) for u in users],
            "total": total,
            "page": page,
            "page_size": page_size
        }

    async def create(
        self,
        db: AsyncSession,
        wechat_id: str,
        name: str,
        email: Optional[str] = None,
        department_id: Optional[str] = None
    ) -> User:
        """
        创建用户

        Args:
            db: 数据库会话
            wechat_id: 企业微信ID
            name: 姓名
            email: 邮箱
            department_id: 部门ID

        Returns:
            User: 创建的用户对象
        """
        # 获取默认角色
        result = await db.execute(
            select(Role).where(Role.name == settings.DEFAULT_ROLE)
        )
        default_role = result.scalar_one_or_none()

        user = User(
            wechat_id=wechat_id,
            name=name,
            email=email,
            department_id=department_id,
            is_active=True,
            roles=[default_role] if default_role else []
        )

        db.add(user)
        await db.commit()
        await db.refresh(user)

        logger.info(f"Created user: {name} ({wechat_id})")

        return user

    async def update(
        self,
        db: AsyncSession,
        user_id: str,
        update_data: Dict[str, Any]
    ) -> User:
        """
        更新用户信息

        Args:
            db: 数据库会话
            user_id: 用户ID
            update_data: 更新数据

        Returns:
            User: 更新后的用户对象
        """
        result = await db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()

        if not user:
            raise ValueError(f"User {user_id} not found")

        for key, value in update_data.items():
            if hasattr(user, key):
                setattr(user, key, value)

        await db.commit()
        await db.refresh(user)

        return user

    async def delete(
        self,
        db: AsyncSession,
        user_id: str
    ):
        """
        删除用户

        Args:
            db: 数据库会话
            user_id: 用户ID
        """
        result = await db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()

        if not user:
            raise ValueError(f"User {user_id} not found")

        await db.delete(user)
        await db.commit()

        logger.info(f"Deleted user: {user.name} ({user_id})")

    async def assign_roles(
        self,
        db: AsyncSession,
        user_id: str,
        role_ids: List[str]
    ):
        """
        分配用户角色

        Args:
            db: 数据库会话
            user_id: 用户ID
            role_ids: 角色ID列表
        """
        # 获取用户
        result = await db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()

        if not user:
            raise ValueError(f"User {user_id} not found")

        # 获取角色对象
        if role_ids:
            roles_result = await db.execute(
                select(Role).where(Role.id.in_(role_ids))
            )
            roles = roles_result.scalars().all()
            user.roles = roles

        await db.commit()
        await db.refresh(user)

        logger.info(f"Assigned roles to user {user_id}: {[r.name for r in user.roles]}")

    async def list_departments(
        self,
        db: AsyncSession
    ) -> List[DepartmentResponse]:
        """
        获取部门列表

        Args:
            db: 数据库会话

        Returns:
            List[DepartmentResponse]: 部门列表
        """
        result = await db.execute(
            select(Department).order_by(Department.code)
        )
        departments = result.scalars().all()

        return [DepartmentResponse.model_validate(d) for d in departments]

    async def list_roles(
        self,
        db: AsyncSession
    ) -> List[RoleResponse]:
        """
        获取角色列表

        Args:
            db: 数据库会话

        Returns:
            List[RoleResponse]: 角色列表
        """
        result = await db.execute(
            select(Role).order_by(Role.name)
        )
        roles = result.scalars().all()

        return [RoleResponse.model_validate(r) for r in roles]


# 全局用户服务实例
user_service = UserService()


def get_user_service() -> UserService:
    """获取用户服务单例"""
    return user_service
