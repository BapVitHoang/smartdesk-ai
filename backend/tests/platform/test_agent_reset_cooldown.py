"""Tests for POST /api/v1/agent/reset-cooldown and its alias (REQ-22, REQ-33)."""

import time
import pytest
from httpx import AsyncClient

from app.core.config import settings
from app.services.llm_service import llm_service


@pytest.mark.asyncio
async def test_reset_cooldown_unauthenticated_rejected(unauth_client: AsyncClient) -> None:
    """Verify unauthenticated request to /agent/reset-cooldown receives HTTP 401."""
    res = await unauth_client.post("/api/v1/agent/reset-cooldown")
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_reset_cooldown_regular_user_forbidden(unauth_client: AsyncClient) -> None:
    """Verify regular user (role != admin) receives HTTP 403 Forbidden."""
    login_res = await unauth_client.post(
        "/api/v1/auth/token",
        json={"username": "an.nguyen@company.vn", "password": settings.DEMO_USER_PASSWORD},
    )
    assert login_res.status_code == 200
    user_token = login_res.json()["access_token"]
    user_headers = {"Authorization": f"Bearer {user_token}"}

    res = await unauth_client.post("/api/v1/agent/reset-cooldown", headers=user_headers)
    assert res.status_code == 403
    assert "Quyền truy cập bị từ chối" in res.json()["detail"]


@pytest.mark.asyncio
async def test_reset_cooldown_admin_success_and_clears_timer(unauth_client: AsyncClient) -> None:
    """Verify admin user receives HTTP 200 and circuit breaker cooldown is cleared."""
    login_res = await unauth_client.post(
        "/api/v1/auth/token",
        json={"username": "admin@smartdesk.ai", "password": settings.DEMO_ADMIN_PASSWORD},
    )
    assert login_res.status_code == 200
    admin_token = login_res.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # Simulate active cooldown lock
    llm_service.cooldown_until = time.time() + 60.0
    assert llm_service.is_in_cooldown() is True

    # Call POST /api/v1/agent/reset-cooldown
    res = await unauth_client.post("/api/v1/agent/reset-cooldown", headers=admin_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert "Circuit breaker cooldown has been reset" in data["message"]
    assert data["cooldown_active"] is False

    # Verify internal state cleared
    assert llm_service.is_in_cooldown() is False


@pytest.mark.asyncio
async def test_reset_cooldown_alias_backward_compatibility(unauth_client: AsyncClient) -> None:
    """Verify legacy alias POST /api/v1/agent/ai-usage/reset-cooldown still works."""
    login_res = await unauth_client.post(
        "/api/v1/auth/token",
        json={"username": "admin@smartdesk.ai", "password": settings.DEMO_ADMIN_PASSWORD},
    )
    assert login_res.status_code == 200
    admin_headers = {"Authorization": f"Bearer {login_res.json()['access_token']}"}

    res = await unauth_client.post("/api/v1/agent/ai-usage/reset-cooldown", headers=admin_headers)
    assert res.status_code == 200
    assert res.json()["status"] == "success"
