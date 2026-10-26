"""Pydantic v2 schemas for OAuth2 authentication, JWT tokens, and RBAC user profiles."""

from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class OAuth2LoginRequest(BaseModel):
    """Payload for Google OAuth2 ID Token or seeded Demo Account login."""
    credential: Optional[str] = Field(None, description="Google OAuth2 JWT ID token")
    email: Optional[EmailStr] = Field(None, description="Demo login email (e.g. admin@smartdesk.ai, an.nguyen@company.vn)")
    provider: str = Field("google", description="Identity provider: 'google' or 'demo'")


class OAuth2PasswordRequest(BaseModel):
    """Payload for OAuth2 password grant login."""
    username: str = Field(..., description="User email as username")
    password: str = Field(..., description="User password")


class AuthUserPayload(BaseModel):
    """Authenticated user info nested in TokenResponse."""
    id: int = Field(..., description="User primary key ID")
    email: str = Field(..., description="User email address")
    full_name: str = Field(..., description="User display name")
    role: str = Field(..., description="User role ('admin' or 'user')")
    workspace_id: int = Field(1, description="Workspace ID")
    avatar_url: Optional[str] = Field(None, description="Avatar image URL")
    is_active: bool = Field(True, description="Account active status")


class TokenResponse(BaseModel):
    """JWT Access Token response model."""
    access_token: str = Field(..., description="HS256 signed JWT access token")
    token_type: str = Field("bearer", description="Token type, default 'bearer'")
    user: AuthUserPayload = Field(..., description="Authenticated user profile")
    # Backwards compatibility top-level aliases
    role: Optional[str] = Field(None, description="Backwards compatible top-level role")
    email: Optional[str] = Field(None, description="Backwards compatible top-level email")
    full_name: Optional[str] = Field(None, description="Backwards compatible top-level full_name")


class UserProfileResponse(BaseModel):
    """Authenticated user profile response model."""
    id: int = Field(..., description="User primary key ID")
    email: str = Field(..., description="User email address")
    full_name: str = Field(..., description="User display name")
    role: str = Field(..., description="User authorization role ('admin' or 'user')")
    oauth_provider: str = Field(..., description="OAuth identity provider ('google' or 'demo')")
    workspace_id: int = Field(..., description="Default workspace ID associated with the user")
    avatar_url: Optional[str] = Field(None, description="Avatar image URL")
    is_active: bool = Field(True, description="Account active status")
