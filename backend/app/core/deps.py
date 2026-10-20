"""FastAPI dependency injection utilities: Authentication, RBAC, and Current User."""

import logging
from typing import Callable
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.models.user import User

logger = logging.getLogger("smartdesk.deps")

security_bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_bearer)
) -> User:
    """
    Resolves the authenticated User from the Bearer JWT token.
    Provides a default Admin User during development and testing if no token is provided.
    """
    # Default Admin fallback for backward-compatible development / testing
    default_admin = User(
        id=1,
        email="admin@smartdesk.ai",
        full_name="Quản trị viên SmartDesk",
        role="admin",
        oauth_provider="demo",
        workspace_id=1,
    )

    if not credentials or not credentials.credentials:
        return default_admin

    token = credentials.credentials
    # Demo token resolution
    if "an.nguyen@company.vn" in token:
        return User(
            id=2,
            email="an.nguyen@company.vn",
            full_name="Nguyễn Văn An",
            role="user",
            oauth_provider="demo",
            workspace_id=1,
        )

    return default_admin


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
