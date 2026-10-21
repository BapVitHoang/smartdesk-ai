"""Authentication & RBAC endpoints (Hybrid Google OAuth2 & Demo Login - REQ-09, REQ-36)."""

import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional
import jwt
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import (
    OAuth2LoginRequest,
    OAuth2PasswordRequest,
    TokenResponse,
    UserProfileResponse,
)

logger = logging.getLogger("smartdesk.api.auth")

router = APIRouter()


def create_access_token(user: User) -> str:
    """Creates a real HS256 signed JWT access token for the given user."""
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    token_payload = {
        "sub": user.email,
        "role": user.role,
        "user_id": user.id,
        "full_name": user.full_name,
        "workspace_id": user.workspace_id,
        "exp": expire,
        "iat": now,
    }
    return jwt.encode(token_payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


@router.post(
    "/oauth2/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="OAuth2 & Demo Login",
    description="Authenticates via Google OAuth2 ID Token or seeded Demo Accounts, issuing an HS256 JWT access token."
)
async def oauth2_login(
    payload: OAuth2LoginRequest,
    db: AsyncSession = Depends(get_db)
) -> TokenResponse:
    """Authenticates user via Google OAuth2 or demo login and issues a signed HS256 JWT token."""
    email: Optional[str] = None
    full_name: Optional[str] = None
    provider: str = payload.provider or "google"

    # 1. Parse Google OAuth2 ID Token credential if provided
    if payload.credential:
        try:
            # Unverified claim extraction for dev/demo or external verification
            claims = jwt.decode(payload.credential, options={"verify_signature": False})
            email = claims.get("email")
            full_name = claims.get("name")
            provider = "google"
        except Exception as exc:
            logger.warning(f"Failed to parse OAuth credential: {exc}")

    # 2. Fallback to direct email payload
    if not email:
        email = payload.email

    if not email:
        # Default to admin demo account
        email = "admin@smartdesk.ai"

    email_clean = str(email).strip().lower()

    # 3. Look up user in seeded database
    result = await db.execute(select(User).where(User.email == email_clean))
    user = result.scalars().first()

    # 4. If user not in DB, dynamically create according to demo/seeded rules
    if not user:
        role = "admin" if "admin" in email_clean else "user"
        if not full_name:
            full_name = "Quản trị viên SmartDesk" if role == "admin" else "Nguyễn Văn An"
        user = User(
            email=email_clean,
            full_name=full_name,
            role=role,
            oauth_provider=provider,
            workspace_id=1,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

    # 5. Generate signed HS256 JWT access token
    access_token = create_access_token(user)

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        role=user.role,
        email=user.email,
        full_name=user.full_name,
    )


@router.post(
    "/token",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="OAuth2 Password Grant Login",
    description="Supports standard OAuth2 Password Grant login (username, password) for test accounts."
)
async def login_for_access_token(
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> TokenResponse:
    """Handles OAuth2 Password Grant login (accepts JSON or x-www-form-urlencoded)."""
    username: str = ""
    password: str = ""

    content_type = request.headers.get("content-type", "")
    if "application/x-www-form-urlencoded" in content_type:
        form_data = await request.form()
        username = str(form_data.get("username", "")).strip()
        password = str(form_data.get("password", "")).strip()
    else:
        try:
            body = await request.json()
            username = str(body.get("username", "")).strip()
            password = str(body.get("password", "")).strip()
        except Exception:
            pass

    if not username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tên người dùng (username/email) không được để trống."
        )

    clean_email = username.lower()
    res = await db.execute(select(User).where(User.email == clean_email))
    user = res.scalars().first()

    if not user:
        # Check if demo login is allowed for test accounts
        if settings.DEMO_LOGIN_ENABLED and ("admin" in clean_email or "an.nguyen" in clean_email):
            role = "admin" if "admin" in clean_email else "user"
            full_name = "Quản trị viên SmartDesk" if role == "admin" else "Nguyễn Văn An"
            user = User(
                email=clean_email,
                full_name=full_name,
                role=role,
                oauth_provider="demo",
                workspace_id=1,
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Tài khoản hoặc mật khẩu không chính xác.",
                headers={"WWW-Authenticate": "Bearer"},
            )

    token = create_access_token(user)
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        role=user.role,
        email=user.email,
        full_name=user.full_name,
    )


@router.get(
    "/me",
    response_model=UserProfileResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Current User Profile",
    description="Returns the profile and role of the currently authenticated user."
)
async def get_me(current_user: User = Depends(get_current_user)) -> UserProfileResponse:
    """Returns profile information of the currently authenticated user."""
    return UserProfileResponse(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        role=current_user.role,
        oauth_provider=current_user.oauth_provider,
        workspace_id=current_user.workspace_id,
    )
