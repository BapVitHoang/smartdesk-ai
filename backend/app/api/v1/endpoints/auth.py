"""Authentication & RBAC endpoints (Google OAuth2 ID token, demo login, password grant - REQ-06, REQ-09, REQ-36)."""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Tuple
import jwt
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.core.deps import get_current_user
from app.core.security import (
    GoogleAuthError,
    get_trusted_client_ip,
    login_throttle,
    verify_google_credential,
    verify_password_async,
)
from app.db.seed.seed_users import DEMO_ACCOUNT_EMAILS
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import (
    DemoLoginRequest,
    GoogleLoginRequest,
    OAuth2LoginRequest,
    TokenResponse,
    UserProfileResponse,
)

logger = logging.getLogger("smartdesk.api.auth")

router = APIRouter()

# One generic message for wrong password, unknown email and inactive account (no account enumeration).
INVALID_CREDENTIALS_MESSAGE = "Tài khoản hoặc mật khẩu không chính xác."
THROTTLED_MESSAGE = "Quá nhiều lần đăng nhập thất bại. Vui lòng thử lại sau ít phút."


def create_access_token(user: User) -> str:
    """Creates a signed JWT access token (algorithm from settings) that always carries an `exp` claim."""
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


def _token_response(user: User) -> TokenResponse:
    """Builds the standard token response for an authenticated user."""
    user_payload = {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role,
        "is_active": user.is_active,
        "workspace_id": user.workspace_id,
        "created_at": user.created_at.isoformat() if hasattr(user, "created_at") and user.created_at else None,
    }
    return TokenResponse(
        access_token=create_access_token(user),
        token_type="bearer",
        role=user.role,
        email=user.email,
        full_name=user.full_name,
        user=user_payload,
    )


def _invalid_credentials() -> HTTPException:
    """Uniform HTTP 401 used for every failed password login."""
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=INVALID_CREDENTIALS_MESSAGE,
        headers={"WWW-Authenticate": "Bearer"},
    )


def _throttled() -> HTTPException:
    """HTTP 429 returned when too many failed attempts were recorded for the email or client IP."""
    return HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail=THROTTLED_MESSAGE,
        headers={"Retry-After": str(settings.LOGIN_THROTTLE_WINDOW_SECONDS)},
    )


def _throttle_keys(request: Request, email: str) -> Tuple[str, str]:
    """Returns the (email, client IP) throttle keys for a login attempt, resolving trusted proxies."""
    client_ip = get_trusted_client_ip(request)
    return f"email:{email}", f"ip:{client_ip}"


@router.post(
    "/oauth2/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="OAuth2 (Google) & Demo Login",
    description=(
        "provider='google': verifies the Google ID token signature, audience, issuer, expiry and email_verified "
        "(501 if GOOGLE_OAUTH_CLIENT_ID is not configured). "
        "provider='demo': one-click login for the seeded demo accounts only; 403 unless DEMO_LOGIN_ENABLED is true. "
        "Issues an HS256 JWT access token."
    ),
)
async def oauth2_login(
    payload: OAuth2LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Authenticates via a verified Google ID token or the seeded demo accounts and issues a signed JWT."""
    provider = (payload.provider or "google").strip().lower()

    if provider == "demo":
        return await _demo_login(payload, db)
    if provider == "google":
        return await _google_login(payload, request, db)
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Nhà cung cấp đăng nhập không được hỗ trợ.",
    )


@router.post(
    "/demo-login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Demo Login (Frontend Client Alias)",
    description="Convenience endpoint matching frontend loginDemo calls for seeded demo accounts.",
)
async def demo_login_alias(
    payload: DemoLoginRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """One-click demo login alias matching frontend client calls."""
    target_email = str(payload.email).strip().lower() if payload.email else ""
    if not target_email and payload.role:
        target_email = "admin@smartdesk.ai" if payload.role == "admin" else "an.nguyen@company.vn"
    if not target_email:
        target_email = "admin@smartdesk.ai"
    req = OAuth2LoginRequest(email=target_email, provider="demo")
    return await _demo_login(req, db)


@router.post(
    "/google",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Google OAuth2 Login (Frontend Client Alias)",
    description="Convenience endpoint matching frontend loginWithGoogle calls.",
)
async def google_login_alias(
    payload: GoogleLoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Google sign-in alias matching frontend loginWithGoogle calls."""
    cred = payload.credential or payload.id_token or ""
    req = OAuth2LoginRequest(credential=cred, provider="google")
    return await _google_login(req, request, db)


async def _demo_login(payload: OAuth2LoginRequest, db: AsyncSession) -> TokenResponse:
    """One-click demo login. Never creates users; only works for seeded demo accounts when enabled."""
    if not settings.DEMO_LOGIN_ENABLED:
        raise _invalid_credentials()

    email = str(payload.email).strip().lower() if payload.email else ""
    forbidden = HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Đăng nhập demo chỉ khả dụng cho các tài khoản demo có sẵn.",
    )
    if email not in DEMO_ACCOUNT_EMAILS:
        raise forbidden

    result = await db.execute(select(User).where(User.email == email))
    user = result.scalars().first()
    if user is None or not user.is_active or user.oauth_provider != "demo":
        raise forbidden
    return _token_response(user)


async def _google_login(payload: OAuth2LoginRequest, request: Request, db: AsyncSession) -> TokenResponse:
    """Verified Google sign-in. New users get role 'user'; admin only via the ADMIN_EMAILS allowlist."""
    if not payload.credential:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Thiếu Google credential (ID token).",
        )

    _, ip_key = _throttle_keys(request, "")
    if login_throttle.is_blocked(ip_key):
        raise _throttled()

    try:
        claims: Dict[str, Any] = await verify_google_credential(payload.credential)
    except GoogleAuthError as exc:
        if exc.status_code != status.HTTP_501_NOT_IMPLEMENTED:
            login_throttle.record_failure(ip_key)
        raise HTTPException(
            status_code=exc.status_code,
            detail=(
                "Đăng nhập Google chưa được cấu hình trên máy chủ."
                if exc.status_code == status.HTTP_501_NOT_IMPLEMENTED
                else "Google credential không hợp lệ."
            ),
        )

    email = str(claims["email"]).strip().lower()
    is_allowlisted_admin = email in settings.ADMIN_EMAILS

    result = await db.execute(select(User).where(User.email == email))
    user: Optional[User] = result.scalars().first()

    if user is None:
        full_name = str(claims.get("name") or email.split("@")[0])[:150]
        user = User(
            email=email,
            full_name=full_name,
            role="admin" if is_allowlisted_admin else "user",
            oauth_provider="google",
            workspace_id=1,
            is_active=True,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
    else:
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Google credential không hợp lệ.",
            )
        if is_allowlisted_admin and user.role != "admin":
            user.role = "admin"
            await db.commit()
            await db.refresh(user)

    return _token_response(user)


@router.post(
    "/token",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="OAuth2 Password Grant Login",
    description=(
        "Standard OAuth2 password grant (username=email, password). Returns the same generic 401 for a wrong "
        "password, unknown email or inactive account; 429 after repeated failures."
    ),
)
async def login_for_access_token(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Handles OAuth2 Password Grant login (accepts JSON or x-www-form-urlencoded)."""
    username: str = ""
    password: str = ""

    content_type = request.headers.get("content-type", "")
    if "application/x-www-form-urlencoded" in content_type:
        form_data = await request.form()
        username = str(form_data.get("username", "")).strip()
        password = str(form_data.get("password", ""))
    else:
        try:
            body = await request.json()
            username = str(body.get("username", "")).strip()
            password = str(body.get("password", ""))
        except Exception:
            pass

    if not username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tên người dùng (username/email) không được để trống.",
        )

    clean_email = username.lower()
    email_key, ip_key = _throttle_keys(request, clean_email)
    if login_throttle.is_blocked(email_key, ip_key):
        raise _throttled()

    res = await db.execute(select(User).where(User.email == clean_email))
    user = res.scalars().first()

    # Always run the (constant-time) hash check so unknown emails take as long as wrong passwords.
    password_ok = await verify_password_async(password, user.password_hash if user else None)
    is_demo_disabled = bool(user and user.oauth_provider == "demo" and not settings.DEMO_LOGIN_ENABLED)
    if not user or not user.is_active or not password_ok or is_demo_disabled:
        login_throttle.record_failure(email_key, ip_key)
        logger.warning("Failed password login attempt from %s", ip_key)
        raise _invalid_credentials()

    login_throttle.reset(email_key)
    return _token_response(user)


@router.get(
    "/me",
    response_model=UserProfileResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Current User Profile",
    description="Returns the profile and role of the currently authenticated user.",
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
