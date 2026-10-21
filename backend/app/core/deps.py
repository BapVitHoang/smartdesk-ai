"""FastAPI dependency injection utilities: Authentication, RBAC, and Current User."""

import logging
from typing import Callable, Optional
from datetime import datetime, timezone
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.db.session import get_db
from app.models.user import User

logger = logging.getLogger("smartdesk.deps")

security_bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Resolves the authenticated User from the Bearer JWT token.
    - Decodes HS256 JWT signed with settings.JWT_SECRET_KEY.
    - Retains backward compatibility for demo tokens ('demo_jwt_token_for_{email}').
    - Returns HTTP 401 Unauthorized if token is missing, invalid, or expired.
    - Allows DEV_AUTH_BYPASS only if explicitly configured in settings.
    """
    if not credentials or not credentials.credentials:
        if settings.DEV_AUTH_BYPASS:
            # Temporary development bypass (must never be True in production)
            return User(
                id=1,
                email="admin@smartdesk.ai",
                full_name="Quản trị viên SmartDesk (Bypass)",
                role="admin",
                oauth_provider="demo",
                workspace_id=1,
            )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Yêu cầu xác thực. Vui lòng cung cấp Bearer token hợp lệ.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials.strip()

    # 1. Backward compatibility for legacy test demo tokens
    if token.startswith("demo_jwt_token_for_"):
        email = token.replace("demo_jwt_token_for_", "").strip().lower()
        role = "admin" if "admin" in email else "user"
        full_name = "Quản trị viên SmartDesk" if role == "admin" else "Nguyễn Văn An"

        # Check DB to get real user ID/workspace_id if available
        res = await db.execute(select(User).where(User.email == email))
        existing_user = res.scalars().first()
        if existing_user:
            return existing_user

        return User(
            id=1 if role == "admin" else 2,
            email=email,
            full_name=full_name,
            role=role,
            oauth_provider="demo",
            workspace_id=1,
        )

    # 2. Real HS256 JWT verification
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        email: Optional[str] = payload.get("sub")
        if not email:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token không hợp lệ: Thiếu thông tin định danh người dùng (sub).",
                headers={"WWW-Authenticate": "Bearer"},
            )

        role: str = payload.get("role", "user")
        user_id: int = payload.get("user_id", 1)
        full_name: str = payload.get("full_name", email)
        workspace_id: int = payload.get("workspace_id", 1)

        # Look up user in database
        res = await db.execute(select(User).where(User.email == email))
        user = res.scalars().first()
        if user:
            return user

        # Fallback to User instance constructed from validated claims
        return User(
            id=user_id,
            email=email,
            full_name=full_name,
            role=role,
            oauth_provider="jwt",
            workspace_id=workspace_id,
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except (jwt.PyJWTError, Exception) as exc:
        logger.warning(f"Failed to decode JWT token: {exc}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token xác thực không hợp lệ: {str(exc)}",
            headers={"WWW-Authenticate": "Bearer"},
        )


def require_role(required_role: str) -> Callable:
    """Enforces that the current authenticated user has the specified role (e.g. 'admin')."""
    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role != required_role and current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Quyền truy cập bị từ chối. Yêu cầu vai trò: '{required_role}'."
            )
        return current_user

    return role_checker
