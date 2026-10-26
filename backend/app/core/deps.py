"""FastAPI dependency injection utilities: Authentication, RBAC, and Current User."""

import logging
from typing import Callable, Optional
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


def _unauthorized(detail: str) -> HTTPException:
    """Builds a uniform HTTP 401 response with the Bearer challenge header."""
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Resolves the authenticated User from the Bearer JWT token.
    - Accepts only HS256 (settings.JWT_ALGORITHM) tokens signed with settings.JWT_SECRET_KEY;
      tokens with any other algorithm (including "none") are rejected.
    - Requires `sub` and `exp` claims; the account must exist in the database and be active.
    - Role is always taken from the database record, never from token claims.
    - Returns HTTP 401 Unauthorized if the token is missing, invalid, expired, or the account is unknown/inactive.
    There is no unauthenticated, bypass, or legacy-token fallback.
    """

    if not credentials or not credentials.credentials:
        raise _unauthorized("Yêu cầu xác thực. Vui lòng cung cấp Bearer token hợp lệ.")

    token = credentials.credentials.strip()

    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            options={"require": ["exp", "sub"]},
        )
    except jwt.ExpiredSignatureError:
        raise _unauthorized("Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.")
    except jwt.PyJWTError as exc:
        logger.warning("Rejected JWT: %s", type(exc).__name__)
        raise _unauthorized("Token xác thực không hợp lệ.")

    email = payload.get("sub")
    if not isinstance(email, str) or not email:
        raise _unauthorized("Token xác thực không hợp lệ.")

    res = await db.execute(select(User).where(User.email == email.strip().lower()))
    user = res.scalars().first()
    if user is None or not user.is_active:
        raise _unauthorized("Token xác thực không hợp lệ.")
    return user


def require_role(required_role: str) -> Callable:
    """Enforces that the current authenticated user has the specified role (e.g. 'admin')."""

    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role != required_role and current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Quyền truy cập bị từ chối. Yêu cầu vai trò: '{required_role}'.",
            )
        return current_user

    return role_checker


require_admin = require_role("admin")
