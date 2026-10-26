"""Pydantic v2 schemas for OAuth2 authentication, JWT tokens, and RBAC user profiles."""

from typing import Any, Dict, Optional
from pydantic import BaseModel, EmailStr, Field


class OAuth2LoginRequest(BaseModel):
    """Payload for Google OAuth2 ID Token or seeded Demo Account login."""

    credential: Optional[str] = Field(None, description="Google OAuth2 JWT ID token")
    email: Optional[EmailStr] = Field(
        None,
        description="Demo login email (e.g. admin@smartdesk.ai, an.nguyen@company.vn)",
    )
    provider: str = Field("google", description="Identity provider: 'google' or 'demo'")


class DemoLoginRequest(BaseModel):
    """Payload for demo login endpoint."""

    email: Optional[EmailStr] = Field(None, description="Demo account email")
    role: Optional[str] = Field(None, description="Demo role ('admin' or 'user')")


class GoogleLoginRequest(BaseModel):
    """Payload for Google OAuth2 ID token login endpoint."""

    id_token: Optional[str] = Field(None, description="Google OAuth2 ID token")
    credential: Optional[str] = Field(
        None, description="Google OAuth2 credential alias"
    )


class OAuth2PasswordRequest(BaseModel):
    """Payload for OAuth2 password grant login."""

    username: str = Field(..., description="User email as username")
    password: str = Field(..., description="User password")


class TokenResponse(BaseModel):
    """JWT Access Token response model."""

    access_token: str = Field(..., description="HS256 signed JWT access token")
    token_type: str = Field("bearer", description="Token type, default 'bearer'")
    role: str = Field(..., description="User role ('admin' or 'user')")
    email: str = Field(..., description="User email address")
    full_name: str = Field(..., description="User full display name")
    user: Optional[Dict[str, Any]] = Field(
        None, description="Detailed user profile object"
    )


class UserProfileResponse(BaseModel):
    """Authenticated user profile response model."""

    id: int = Field(..., description="User primary key ID")
    email: str = Field(..., description="User email address")
    full_name: str = Field(..., description="User display name")
    role: str = Field(..., description="User authorization role ('admin' or 'user')")
    oauth_provider: str = Field(
        ..., description="OAuth identity provider ('google' or 'demo')"
    )
    workspace_id: int = Field(
        ..., description="Default workspace ID associated with the user"
    )
    avatar_url: Optional[str] = Field(None, description="Google profile picture URL")
    is_active: bool = Field(True, description="Whether the account is active")
