"""Seed initial admin and customer test accounts for OAuth2 / RBAC (REQ-09, REQ-39)."""

import logging
from typing import Set
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import hash_password
from app.models.user import User

logger = logging.getLogger("smartdesk.seed.users")

DEMO_ACCOUNT_EMAILS: Set[str] = {
    "admin@smartdesk.ai",
    "an.nguyen@company.vn",
}


async def seed_users(session: AsyncSession) -> None:
    """Seeds default Admin and Customer accounts with salted password hashes if users table is empty and DEMO_LOGIN_ENABLED is True."""
    if not settings.DEMO_LOGIN_ENABLED:
        logger.info("DEMO_LOGIN_ENABLED is False; skipping demo accounts seeding.")
        return

    res = await session.execute(select(User))
    existing_users = {u.email: u for u in res.scalars().all()}

    if not existing_users:
        admin_user = User(
            email="admin@smartdesk.ai",
            full_name="Quản trị viên SmartDesk",
            role="admin",
            oauth_provider="demo",
            workspace_id=1,
            password_hash=hash_password(settings.DEMO_ADMIN_PASSWORD),
            is_active=True,
        )
        regular_user = User(
            email="an.nguyen@company.vn",
            full_name="Nguyễn Văn An",
            role="user",
            oauth_provider="demo",
            workspace_id=1,
            password_hash=hash_password(settings.DEMO_USER_PASSWORD),
            is_active=True,
        )
        session.add(admin_user)
        session.add(regular_user)
        await session.commit()
        logger.info("Seeded default test accounts: admin@smartdesk.ai and an.nguyen@company.vn")
    else:
        # Ensure existing demo accounts have valid password hashes and active status
        updated = False
        if "admin@smartdesk.ai" in existing_users:
            u = existing_users["admin@smartdesk.ai"]
            if not u.password_hash:
                u.password_hash = hash_password(settings.DEMO_ADMIN_PASSWORD)
                u.oauth_provider = "demo"
                updated = True
            if not u.is_active:
                u.is_active = True
                updated = True
        if "an.nguyen@company.vn" in existing_users:
            u = existing_users["an.nguyen@company.vn"]
            if not u.password_hash:
                u.password_hash = hash_password(settings.DEMO_USER_PASSWORD)
                u.oauth_provider = "demo"
                updated = True
            if not u.is_active:
                u.is_active = True
                updated = True
        if updated:
            await session.commit()
            logger.info("Synchronized password hashes for existing demo user accounts.")
