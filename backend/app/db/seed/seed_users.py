"""Seed initial admin and customer test accounts for OAuth2 / RBAC (REQ-09, REQ-39)."""

import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User

logger = logging.getLogger("smartdesk.seed.users")


async def seed_users(session: AsyncSession) -> None:
    """Seeds default Admin and Customer accounts if users table is empty."""
    res = await session.execute(select(User).limit(1))
    if res.scalars().first():
        return

    sample_users = [
        User(
            email="admin@smartdesk.ai",
            full_name="Quản trị viên SmartDesk",
            role="admin",
            oauth_provider="google",
            workspace_id=1,
        ),
        User(
            email="an.nguyen@company.vn",
            full_name="Nguyễn Văn An",
            role="user",
            oauth_provider="google",
            workspace_id=1,
        ),
    ]

    for user in sample_users:
        session.add(user)
    await session.commit()
    logger.info(f"Seeded {len(sample_users)} test user accounts (admin, user).")
