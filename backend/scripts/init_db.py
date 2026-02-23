"""
数据库初始化脚本
创建初始数据（默认角色、部门等）
"""
import asyncio
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import async_session_maker
from app.models.department import Department
from app.models.role import Role
from app.models.user import User
from app.core.security import get_password_hash
from app.core.constants import ROLE_PERMISSIONS


async def init_default_data() -> None:
    """
    初始化默认数据
    """
    async with async_session_maker() as session:
        # ===== 创建默认部门 =====
        default_departments = [
            {"name": "公司总部", "code": "HQ", "parent_id": None},
            {"name": "人力资源部", "code": "HR", "parent_id": None},
            {"name": "财务部", "code": "FIN", "parent_id": None},
            {"name": "行政部", "code": "ADMIN", "parent_id": None},
            {"name": "IT部", "code": "IT", "parent_id": None},
            {"name": "法务部", "code": "LEGAL", "parent_id": None},
            {"name": "市场部", "code": "MKT", "parent_id": None},
            {"name": "销售部", "code": "SALES", "parent_id": None},
            {"name": "研发部", "code": "R&D", "parent_id": None},
        ]

        for dept_data in default_departments:
            existing = await session.execute(
                select(Department).where(Department.code == dept_data["code"])
            )
            if not existing.scalar_one_or_none():
                dept = Department(**dept_data)
                session.add(dept)
        await session.commit()

        # ===== 创建默认角色 =====
        for role_name, permissions in ROLE_PERMISSIONS.items():
            existing = await session.execute(
                select(Role).where(Role.name == role_name)
            )
            if not existing.scalar_one_or_none():
                role = Role(
                    name=role_name,
                    description=get_role_description(role_name),
                    permissions=permissions
                )
                session.add(role)
        await session.commit()

        # ===== 创建默认管理员账户 =====
        existing_admin = await session.execute(
            select(User).where(User.name == "admin")
        )
        if not existing_admin.scalar_one_or_none():
            # 获取SUPER_ADMIN角色
            admin_role_result = await session.execute(
                select(Role).where(Role.name == "SUPER_ADMIN")
            )
            admin_role = admin_role_result.scalar_one_or_none()

            if admin_role:
                admin_user = User(
                    wechat_id="admin",
                    name="系统管理员",
                    email="admin@enterprise.com",
                    department_id=None,
                    password_hash=get_password_hash("admin123"),  # 默认密码
                    is_active=True,
                    roles=[admin_role]
                )
                session.add(admin_user)
                await session.commit()

        print("✓ Default data initialized successfully")
        print("  - Default departments created")
        print("  - Default roles created")
        print("  - Admin user created (username: admin, password: admin123)")


def get_role_description(role_name: str) -> str:
    """
    获取角色描述

    Args:
        role_name: 角色名称

    Returns:
        str: 角色描述
    """
    descriptions = {
        "SUPER_ADMIN": "系统超级管理员，拥有所有权限",
        "DEPT_ADMIN": "部门管理员，管理本部门文档和用户",
        "CONTENT_EDITOR": "内容编辑，负责文档上传和编辑",
        "CONTENT_AUDITOR": "内容审核，负责文档审核",
        "REGULAR_USER": "普通用户，可以查询和使用系统",
    }
    return descriptions.get(role_name, role_name)


if __name__ == "__main__":
    print("Initializing default data...")
    asyncio.run(init_default_data())
