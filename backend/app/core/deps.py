"""FastAPI dependency injection utilities: Authentication, RBAC, and Current User."""

import logging
from typing import Callable
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.core.config import settings
from app.models.user import User

logger = logging.getLogger("smartdesk.deps")

security_bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_bearer)
) -> User:
    """
    Resolves the authenticated User from the Bearer JWT token.
    Default behavior: HTTP 401 Unauthorized without a valid Bearer token.
    A development bypass is allowed only when settings.DEV_AUTH_BYPASS is True.
    NOTE: The stub fallback below is temporary and must be replaced by Dev B with full JWT verification.
    """
    if not credentials or not credentials.credentials:
        if settings.DEV_AUTH_BYPASS:
            # Temporary development bypass (must never be True in production or demo)
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

    token = credentials.credentials
    # Demo token resolution stub (Dev B will replace with real jwt.decode)
    if "an.nguyen@company.vn" in token:
        return User(
            id=2,
            email="an.nguyen@company.vn",
            full_name="Nguyễn Văn An",
            role="user",
            oauth_provider="demo",
            workspace_id=1,
        )

    return User(
        id=1,
        email="admin@smartdesk.ai",
        full_name="Quản trị viên SmartDesk",
        role="admin",
        oauth_provider="demo",
        workspace_id=1,
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
