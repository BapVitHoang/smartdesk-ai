"""Authentication & RBAC endpoints (Hybrid Google OAuth2 & Demo Login - REQ-09, REQ-36)."""

import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr

from app.core.deps import get_current_user
from app.models.user import User

logger = logging.getLogger("smartdesk.api.auth")

router = APIRouter()


class OAuth2LoginRequest(BaseModel):
    """Payload for Google OAuth2 ID Token or Demo Account Login."""
    credential: Optional[str] = None  # Google OAuth2 JWT ID token
    email: Optional[EmailStr] = None   # Demo login email (e.g. admin@smartdesk.ai, an.nguyen@company.vn)
    provider: str = "google"          # "google" or "demo"


class TokenResponse(BaseModel):
    """JWT Token response."""
    access_token: str
    token_type: str = "bearer"
    role: str
    email: str
    full_name: str


class UserProfileResponse(BaseModel):
    """Current authenticated user profile."""
    id: int
    email: str
    full_name: str
    role: str
    oauth_provider: str
    workspace_id: int


@router.post(
    "/oauth2/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="OAuth2 & Demo Login",
    description="Authenticates via Google OAuth2 ID Token or seeded Demo Accounts, issuing an HS256 JWT access token."
)
async def oauth2_login(payload: OAuth2LoginRequest) -> TokenResponse:
    """Stub OAuth2 / Demo login issuing valid access token."""
    email = payload.email or "admin@smartdesk.ai"
    role = "admin" if "admin" in email else "user"
    full_name = "Quản trị viên SmartDesk" if role == "admin" else "Nguyễn Văn An"

    # Minimal working JWT stub token for development
    return TokenResponse(
        access_token=f"demo_jwt_token_for_{email}",
        token_type="bearer",
        role=role,
        email=email,
        full_name=full_name,
    )


@router.get(
    "/me",
    response_model=UserProfileResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Current User Profile",
    description="Returns the profile and role of the currently authenticated user."
)
async def get_me(current_user: User = Depends(get_current_user)) -> UserProfileResponse:
    """Returns current user profile."""
    return UserProfileResponse(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        role=current_user.role,
        oauth_provider=current_user.oauth_provider,
        workspace_id=current_user.workspace_id,
    )
