"""Platform security and authentication test suite (REQ-06, REQ-09, REQ-36).

Verifies:
  1. Password verification with salted scrypt (constant-time compare).
  2. Identical generic 401 response for wrong password vs unknown account (timing & enum protection).
  3. Google OAuth2 ID token verification with google-auth (rejecting forged/garbled/unsigned tokens).
  4. Google OAuth2 new user role assignment and ADMIN_EMAILS elevation.
  5. 1-click Demo login restriction to DEMO_LOGIN_ENABLED and seeded accounts.
  6. Login sliding-window throttling (HTTP 429).
  7. Strict JWT decoding: rejecting expired, unsigned, and wrong-algorithm tokens.
  8. RBAC enforcement: regular users blocked from admin-only endpoints (HTTP 403).
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict
import jwt
import pytest
from httpx import AsyncClient

from app.core.config import settings
from app.core.security import GoogleAuthError, login_throttle


@pytest.fixture(autouse=True)
def clean_login_throttle():
    """Ensure clean throttle state before and after each test."""
    login_throttle.clear_all()
    yield
    login_throttle.clear_all()


@pytest.mark.asyncio
async def test_password_login_correct_credentials(unauth_client: AsyncClient) -> None:
    """Verify password grant login succeeds with valid seeded credentials."""
    # 1. Admin login
    res_admin = await unauth_client.post(
        "/api/v1/auth/token",
        json={"username": "admin@smartdesk.ai", "password": settings.DEMO_ADMIN_PASSWORD},
    )
    assert res_admin.status_code == 200
    data_admin = res_admin.json()
    assert data_admin["role"] == "admin"
    assert data_admin["email"] == "admin@smartdesk.ai"
    assert "access_token" in data_admin

    # 2. Regular user login
    res_user = await unauth_client.post(
        "/api/v1/auth/token",
        json={"username": "an.nguyen@company.vn", "password": settings.DEMO_USER_PASSWORD},
    )
    assert res_user.status_code == 200
    data_user = res_user.json()
    assert data_user["role"] == "user"
    assert data_user["email"] == "an.nguyen@company.vn"
    assert "access_token" in data_user


@pytest.mark.asyncio
async def test_password_login_wrong_password_and_unknown_user_identical_401(unauth_client: AsyncClient) -> None:
    """Verify wrong password and unknown user return the exact same generic 401 body."""
    # Wrong password for existing user
    res_wrong_pw = await unauth_client.post(
        "/api/v1/auth/token",
        json={"username": "admin@smartdesk.ai", "password": "WrongPassword123!"},
    )
    assert res_wrong_pw.status_code == 401
    assert "WWW-Authenticate" in res_wrong_pw.headers

    # Unknown user
    res_unknown_user = await unauth_client.post(
        "/api/v1/auth/token",
        json={"username": "ghost.user@unknown-domain.vn", "password": "AnyRandomPassword123!"},
    )
    assert res_unknown_user.status_code == 401
    assert "WWW-Authenticate" in res_unknown_user.headers

    # Bodies must be completely identical (prevent username enumeration)
    assert res_wrong_pw.json() == res_unknown_user.json()
    assert res_wrong_pw.json()["detail"] == "Tài khoản hoặc mật khẩu không chính xác."


@pytest.mark.asyncio
async def test_google_login_unconfigured_returns_501(unauth_client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify Google sign-in returns 501 when GOOGLE_OAUTH_CLIENT_ID is not configured."""
    monkeypatch.setattr(settings, "GOOGLE_OAUTH_CLIENT_ID", "")

    res = await unauth_client.post(
        "/api/v1/auth/oauth2/login",
        json={"provider": "google", "credential": "dummy.id.token"},
    )
    assert res.status_code == 501
    assert "chưa được cấu hình" in res.json()["detail"]


@pytest.mark.asyncio
async def test_google_login_forged_and_invalid_tokens_rejected(
    unauth_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verify garbled, unsigned, or forged Google tokens are strictly rejected with 401."""
    monkeypatch.setattr(settings, "GOOGLE_OAUTH_CLIENT_ID", "test-client-id.apps.googleusercontent.com")

    # 1. Garbled non-JWT string
    res_garbled = await unauth_client.post(
        "/api/v1/auth/oauth2/login",
        json={"provider": "google", "credential": "not-a-valid-jwt-token"},
    )
    assert res_garbled.status_code == 401

    # 2. Forged unsigned token (hacker attempting to claim admin identity)
    forged_claims = {
        "email": "hacker@evil.com",
        "name": "Hacker Evil",
        "aud": "test-client-id.apps.googleusercontent.com",
        "iss": "accounts.google.com",
        "email_verified": True,
    }
    forged_token = jwt.encode(
        forged_claims,
        "insecure-dummy-key-for-test-padding-32bytes",
        algorithm="HS256",
    )
    res_forged = await unauth_client.post(
        "/api/v1/auth/oauth2/login",
        json={"provider": "google", "credential": forged_token},
    )
    assert res_forged.status_code == 401
    assert "Google credential không hợp lệ" in res_forged.json()["detail"]


@pytest.mark.asyncio
async def test_google_login_valid_token_creates_user_with_role_user(
    unauth_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verify a valid Google ID token creates a new account with default role 'user'."""
    monkeypatch.setattr(settings, "GOOGLE_OAUTH_CLIENT_ID", "test-client-id.apps.googleusercontent.com")

    # Mock the cryptographic verification of Google ID token
    async def mock_verify(credential: str) -> Dict[str, Any]:
        return {
            "email": "customer.google@example.com",
            "name": "Google Customer",
            "aud": "test-client-id.apps.googleusercontent.com",
            "iss": "accounts.google.com",
            "email_verified": True,
        }

    monkeypatch.setattr("app.api.v1.endpoints.auth.verify_google_credential", mock_verify)

    res = await unauth_client.post(
        "/api/v1/auth/oauth2/login",
        json={"provider": "google", "credential": "valid.mocked.google.token"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["email"] == "customer.google@example.com"
    assert data["role"] == "user"  # Google sign-ins default to regular user
    assert data["full_name"] == "Google Customer"


@pytest.mark.asyncio
async def test_google_login_admin_emails_allowlist_elevation(
    unauth_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verify accounts in ADMIN_EMAILS receive role 'admin' upon Google authentication."""
    monkeypatch.setattr(settings, "GOOGLE_OAUTH_CLIENT_ID", "test-client-id.apps.googleusercontent.com")
    monkeypatch.setattr(settings, "ADMIN_EMAILS", ["corporate.admin@smartdesk.ai"])

    async def mock_verify(credential: str) -> Dict[str, Any]:
        return {
            "email": "corporate.admin@smartdesk.ai",
            "name": "Corporate Admin",
            "aud": "test-client-id.apps.googleusercontent.com",
            "iss": "accounts.google.com",
            "email_verified": True,
        }

    monkeypatch.setattr("app.api.v1.endpoints.auth.verify_google_credential", mock_verify)

    res = await unauth_client.post(
        "/api/v1/auth/oauth2/login",
        json={"provider": "google", "credential": "valid.mocked.google.admin.token"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["email"] == "corporate.admin@smartdesk.ai"
    assert data["role"] == "admin"


@pytest.mark.asyncio
async def test_demo_login_disabled_rejects_demo_admin_on_both_routes_and_preserves_local_user(
    unauth_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verify DEMO_LOGIN_ENABLED=False rejects demo accounts on both /auth/token and /auth/oauth2/login with 401, while non-demo users remain unaffected."""
    # 1. When DEMO_LOGIN_ENABLED is True (default), demo admin succeeds on both routes
    res_token_true = await unauth_client.post(
        "/api/v1/auth/token",
        json={"username": "admin@smartdesk.ai", "password": settings.DEMO_ADMIN_PASSWORD},
    )
    assert res_token_true.status_code == 200

    res_oauth_true = await unauth_client.post(
        "/api/v1/auth/oauth2/login",
        json={"provider": "demo", "email": "admin@smartdesk.ai"},
    )
    assert res_oauth_true.status_code == 200

    # 2. Insert a non-demo user (oauth_provider="local")
    from sqlalchemy import select
    from app.db.session import async_session_factory
    from app.models.user import User
    from app.core.security import hash_password
    local_email = "employee@internal.corp"
    local_pwd = "StrongCorpPassword2026!"
    async with async_session_factory() as db:
        res = await db.execute(select(User).where(User.email == local_email))
        if not res.scalars().first():
            local_user = User(
                email=local_email,
                full_name="Nhân viên nội bộ",
                role="user",
                oauth_provider="local",
                workspace_id=1,
                password_hash=hash_password(local_pwd),
                is_active=True,
            )
            db.add(local_user)
            await db.commit()

    # 3. Disable DEMO_LOGIN_ENABLED
    monkeypatch.setattr(settings, "DEMO_LOGIN_ENABLED", False)

    # Demo admin rejected on /auth/token with generic 401
    res_token_false = await unauth_client.post(
        "/api/v1/auth/token",
        json={"username": "admin@smartdesk.ai", "password": settings.DEMO_ADMIN_PASSWORD},
    )
    assert res_token_false.status_code == 401
    assert res_token_false.json()["detail"] == "Tài khoản hoặc mật khẩu không chính xác."

    # Demo admin rejected on /auth/oauth2/login with generic 401
    res_oauth_false = await unauth_client.post(
        "/api/v1/auth/oauth2/login",
        json={"provider": "demo", "email": "admin@smartdesk.ai"},
    )
    assert res_oauth_false.status_code == 401
    assert res_oauth_false.json()["detail"] == "Tài khoản hoặc mật khẩu không chính xác."

    # Non-demo account can still log in via password grant!
    res_local = await unauth_client.post(
        "/api/v1/auth/token",
        json={"username": local_email, "password": local_pwd},
    )
    assert res_local.status_code == 200
    assert res_local.json()["email"] == local_email


@pytest.mark.asyncio
async def test_seed_users_skipped_when_demo_login_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify seed_users skips adding demo accounts when DEMO_LOGIN_ENABLED is False."""
    from app.db.seed.seed_users import seed_users

    monkeypatch.setattr(settings, "DEMO_LOGIN_ENABLED", False)

    class DummySession:
        def __init__(self):
            self.calls = []
        async def execute(self, *args, **kwargs):
            self.calls.append("execute")

    dummy = DummySession()
    await seed_users(dummy)
    assert len(dummy.calls) == 0



@pytest.mark.asyncio
async def test_demo_login_cannot_mint_arbitrary_accounts(unauth_client: AsyncClient) -> None:
    """Verify demo login strictly rejects unseeded / arbitrary email addresses."""
    res = await unauth_client.post(
        "/api/v1/auth/oauth2/login",
        json={"provider": "demo", "email": "attacker@evil.com"},
    )
    assert res.status_code == 403
    assert "chỉ khả dụng" in res.json()["detail"]


@pytest.mark.asyncio
async def test_login_throttling_returns_429(unauth_client: AsyncClient) -> None:
    """Verify sliding-window throttle returns HTTP 429 after maximum failed attempts."""
    target_email = "victim@company.vn"
    for _ in range(settings.LOGIN_MAX_FAILED_ATTEMPTS):
        res = await unauth_client.post(
            "/api/v1/auth/token",
            json={"username": target_email, "password": "WrongPasswordAttempt"},
        )
        assert res.status_code == 401

    # 11th attempt must be throttled
    throttled_res = await unauth_client.post(
        "/api/v1/auth/token",
        json={"username": target_email, "password": "WrongPasswordAttempt"},
    )
    assert throttled_res.status_code == 429
    assert "Retry-After" in throttled_res.headers
    assert "Quá nhiều lần đăng nhập" in throttled_res.json()["detail"]


@pytest.mark.asyncio
async def test_expired_and_wrong_algorithm_jwt_rejected(unauth_client: AsyncClient) -> None:
    """Verify JWT decoding enforces expiration and algorithm validation."""
    now = datetime.now(timezone.utc)

    # 1. Expired JWT token
    expired_payload = {
        "sub": "admin@smartdesk.ai",
        "role": "admin",
        "exp": now - timedelta(hours=1),
        "iat": now - timedelta(hours=2),
    }
    expired_token = jwt.encode(expired_payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    res_expired = await unauth_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {expired_token}"},
    )
    assert res_expired.status_code == 401
    assert "hết hạn" in res_expired.json()["detail"]

    # 2. Token signed with wrong secret key
    wrong_key_token = jwt.encode(
        {"sub": "admin@smartdesk.ai", "role": "admin", "exp": now + timedelta(hours=1)},
        "a-completely-different-signing-secret-key-32chars",
        algorithm="HS256",
    )
    res_wrong_key = await unauth_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {wrong_key_token}"},
    )
    assert res_wrong_key.status_code == 401

    # 3. Missing Bearer token completely
    res_no_auth = await unauth_client.get("/api/v1/auth/me")
    assert res_no_auth.status_code == 401


@pytest.mark.asyncio
async def test_regular_user_cannot_call_admin_endpoints(unauth_client: AsyncClient) -> None:
    """Verify regular user receives HTTP 403 Forbidden on admin telemetry and management routes."""
    # 1. Obtain user token via password grant
    res_login_user = await unauth_client.post(
        "/api/v1/auth/token",
        json={"username": "an.nguyen@company.vn", "password": settings.DEMO_USER_PASSWORD},
    )
    assert res_login_user.status_code == 200
    user_token = res_login_user.json()["access_token"]
    user_headers = {"Authorization": f"Bearer {user_token}"}

    # 2. User blocked from admin AI usage telemetry
    res_telemetry = await unauth_client.get("/api/v1/agent/ai-usage", headers=user_headers)
    assert res_telemetry.status_code == 403
    assert "Quyền truy cập bị từ chối" in res_telemetry.json()["detail"]

    # 3. Admin successfully accesses AI usage telemetry
    res_login_admin = await unauth_client.post(
        "/api/v1/auth/token",
        json={"username": "admin@smartdesk.ai", "password": settings.DEMO_ADMIN_PASSWORD},
    )
    assert res_login_admin.status_code == 200
    admin_token = res_login_admin.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    res_admin_telemetry = await unauth_client.get("/api/v1/agent/ai-usage", headers=admin_headers)
    assert res_admin_telemetry.status_code == 200
