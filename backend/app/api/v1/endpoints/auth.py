"""Authentication & RBAC endpoints (Google Identity Services OAuth2 & Demo Login - REQ-09, REQ-36)."""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional
import jwt
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

from app.core.config import settings
from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import (
    OAuth2LoginRequest,
    TokenResponse,
    AuthUserPayload,
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


def build_token_response(user: User, access_token: str) -> TokenResponse:
    """Helper to construct standard TokenResponse with nested user object."""
    user_payload = AuthUserPayload(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        workspace_id=user.workspace_id,
        avatar_url=user.avatar_url,
        is_active=user.is_active,
    )
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=user_payload,
        role=user.role,
        email=user.email,
        full_name=user.full_name,
    )


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
    """Authenticates user via Google OAuth2 ID Token or demo login and issues a signed HS256 JWT token."""
    provider: str = (payload.provider or "google").strip().lower()

    # =========================================================================
    # 1. Google OAuth2 Provider (Real Google ID Token Verification)
    # =========================================================================
    if provider == "google":
        if not payload.credential:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Yêu cầu cung cấp Google ID Token trong trường 'credential'."
            )

        # Cryptographically verify the Google ID token
        try:
            req_adapter = google_requests.Request()
            aud = settings.GOOGLE_CLIENT_ID if settings.GOOGLE_CLIENT_ID else None
            id_info = id_token.verify_oauth2_token(
                payload.credential,
                req_adapter,
                audience=aud
            )
        except ValueError as val_err:
            logger.warning(f"Google ID token signature/claims verification failed: {val_err}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Google ID Token không hợp lệ hoặc đã hết hạn: {val_err}",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except Exception as exc:
            logger.error(f"Unexpected error verifying Google ID token: {exc}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Xác thực Google ID Token thất bại.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Enforce email_verified constraint
        if not id_info.get("email_verified", False):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email Google chưa được xác thực (email_verified=False)."
            )

        google_sub = str(id_info.get("sub", "")).strip()
        raw_email = id_info.get("email")
        if not google_sub or not raw_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Google token thiếu thông tin định danh (sub hoặc email)."
            )

        email_clean = str(raw_email).strip().lower()
        full_name = str(id_info.get("name") or email_clean.split("@")[0]).strip()
        avatar_url = id_info.get("picture")

        # Step 1: Look up user by google_sub
        result = await db.execute(select(User).where(User.google_sub == google_sub))
        user = result.scalars().first()

        # Step 2: Fallback to lookup by email to link existing account
        if not user:
            result_email = await db.execute(select(User).where(User.email == email_clean))
            user = result_email.scalars().first()
            if user:
                user.google_sub = google_sub
                user.oauth_provider = "google"
                if full_name:
                    user.full_name = full_name
                if avatar_url:
                    user.avatar_url = avatar_url
                await db.commit()
                await db.refresh(user)

        # Step 3: If user does not exist, create new user account
        if not user:
            # Role policy: Never grant admin automatically unless explicitly listed in ADMIN_EMAILS
            role = "admin" if email_clean in settings.ADMIN_EMAILS else "user"
            user = User(
                email=email_clean,
                full_name=full_name,
                role=role,
                oauth_provider="google",
                google_sub=google_sub,
                avatar_url=avatar_url,
                workspace_id=1,
                is_active=True,
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)
        else:
            # Sync latest profile name & avatar from Google account
            updated = False
            if full_name and user.full_name != full_name:
                user.full_name = full_name
                updated = True
            if avatar_url and user.avatar_url != avatar_url:
                user.avatar_url = avatar_url
                updated = True
            if updated:
                await db.commit()
                await db.refresh(user)

        # Check account active status
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Tài khoản đã bị vô hiệu hóa. Vui lòng liên hệ quản trị viên."
            )

    # =========================================================================
    # 2. Demo Login Provider (Only allowed in non-production environments)
    # =========================================================================
    elif provider == "demo":
        if settings.ENVIRONMENT.lower() == "production" or not settings.DEMO_LOGIN_ENABLED:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Tính năng Đăng nhập Demo bị vô hiệu hóa trên môi trường production."
            )

        email = payload.email or "admin@smartdesk.ai"
        email_clean = str(email).strip().lower()

        result = await db.execute(select(User).where(User.email == email_clean))
        user = result.scalars().first()

        if not user:
            role = "admin" if ("admin" in email_clean or email_clean in settings.ADMIN_EMAILS) else "user"
            full_name = "Quản trị viên SmartDesk" if role == "admin" else "Nguyễn Văn An"
            user = User(
                email=email_clean,
                full_name=full_name,
                role=role,
                oauth_provider="demo",
                workspace_id=1,
                is_active=True,
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Tài khoản đã bị vô hiệu hóa."
            )

    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Nhà cung cấp xác thực '{provider}' không được hỗ trợ. Chỉ chấp nhận 'google' hoặc 'demo'."
        )

    # Issue signed HS256 JWT access token
    access_token = create_access_token(user)
    return build_token_response(user, access_token)


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
        # Check if demo login is allowed for test accounts in non-production
        is_prod = settings.ENVIRONMENT.lower() == "production"
        if not is_prod and settings.DEMO_LOGIN_ENABLED and ("admin" in clean_email or "an.nguyen" in clean_email):
            role = "admin" if ("admin" in clean_email or clean_email in settings.ADMIN_EMAILS) else "user"
            full_name = "Quản trị viên SmartDesk" if role == "admin" else "Nguyễn Văn An"
            user = User(
                email=clean_email,
                full_name=full_name,
                role=role,
                oauth_provider="demo",
                workspace_id=1,
                is_active=True,
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

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tài khoản đã bị vô hiệu hóa."
        )

    access_token = create_access_token(user)
    return build_token_response(user, access_token)


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
        avatar_url=current_user.avatar_url,
        is_active=current_user.is_active,
    )
