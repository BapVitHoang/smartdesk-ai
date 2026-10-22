"""Cross-feature offline flows (Dev C / Owner 3): login -> list tickets -> create ticket -> ask chat -> confirm action.

These tests chain several modules through the real HTTP layer using real HS256 tokens issued by
``POST /api/v1/auth/oauth2/login`` (no ``get_current_user`` override) and the deterministic offline
RAG / tool pipeline, so they require no Gemini key and no network.
"""

from typing import Dict

import pytest
from httpx import AsyncClient

CUSTOMER_EMAIL = "an.nguyen@company.vn"
ADMIN_EMAIL = "admin@smartdesk.ai"


async def _login(client: AsyncClient, email: str) -> Dict[str, str]:
    """Logs in through the demo OAuth2 endpoint and returns Bearer headers."""
    res = await client.post("/api/v1/auth/oauth2/login", json={"email": email, "provider": "demo"})
    assert res.status_code == 200
    body = res.json()
    assert body["email"] == email
    return {"Authorization": f"Bearer {body['access_token']}"}


@pytest.mark.asyncio
async def test_customer_flow_login_list_create_chat_confirm(unauth_client: AsyncClient) -> None:
    """Customer journey end to end; the confirmed escalation ticket becomes visible to the agent."""
    headers = await _login(unauth_client, CUSTOMER_EMAIL)

    # 1. The token resolves to the customer profile.
    me = await unauth_client.get("/api/v1/auth/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["role"] == "user"

    # 2. List tickets (baseline for the customer).
    before = await unauth_client.get("/api/v1/tickets", headers=headers)
    assert before.status_code == 200
    before_ids = {t["ticket_code"] for t in before.json()}

    # 3. Create a ticket through the form endpoint.
    created = await unauth_client.post(
        "/api/v1/tickets",
        headers=headers,
        json={
            "customer_name": "Nguyễn Văn An",
            "customer_email": CUSTOMER_EMAIL,
            "category": "Billing",
            "priority": "High",
            "subject": "Cross-feature flow: hóa đơn tháng 10",
            "description": "Cần kiểm tra lại hóa đơn tháng 10 của tôi.",
        },
    )
    assert created.status_code == 201
    new_ticket = created.json()
    assert new_ticket["ticket_code"].startswith("#TICK-")

    after = await unauth_client.get("/api/v1/tickets", headers=headers)
    assert after.status_code == 200
    after_ids = {t["ticket_code"] for t in after.json()}
    assert new_ticket["ticket_code"] in after_ids
    assert after_ids - before_ids == {new_ticket["ticket_code"]}

    # 4. Ask the chat to open an escalation ticket -> two-phase pending action, nothing created yet.
    chat = await unauth_client.post(
        "/api/v1/chat",
        headers=headers,
        json={"message": "Tạo giúp tôi ticket lỗi cổng thanh toán VNPAY mức Urgent", "workspace_id": 1},
    )
    assert chat.status_code == 200
    chat_body = chat.json()
    assert "create_escalation_ticket" in chat_body.get("tools_called", [])
    pending = chat_body.get("pending_action")
    assert pending is not None and pending["requires_confirmation"] is True

    # 5. Confirm the action -> ticket is really created.
    confirm = await unauth_client.post(
        "/api/v1/chat/confirm-action",
        headers=headers,
        json={"action_id": pending["action_id"], "confirmed": True},
    )
    assert confirm.status_code == 200
    confirm_body = confirm.json()
    assert confirm_body["executed"] is True
    escalated_id = confirm_body["ticket_id"]
    assert escalated_id.startswith("#TICK-")

    # 6. The agent (admin) sees both tickets in the queue.
    admin_headers = await _login(unauth_client, ADMIN_EMAIL)
    queue = await unauth_client.get("/api/v1/tickets?limit=100", headers=admin_headers)
    assert queue.status_code == 200
    queue_ids = {t["ticket_code"] for t in queue.json()}
    assert new_ticket["ticket_code"] in queue_ids
    assert escalated_id in queue_ids


@pytest.mark.asyncio
async def test_cancelled_confirmation_does_not_create_ticket(unauth_client: AsyncClient) -> None:
    """Cancelling a pending chat action must not execute it nor create a ticket."""
    headers = await _login(unauth_client, ADMIN_EMAIL)

    before = await unauth_client.get("/api/v1/tickets?limit=100", headers=headers)
    count_before = len(before.json())

    chat = await unauth_client.post(
        "/api/v1/chat",
        headers=headers,
        json={"message": "Tạo giúp tôi ticket lỗi đăng nhập mức Urgent", "workspace_id": 1},
    )
    assert chat.status_code == 200
    pending = chat.json().get("pending_action")
    assert pending is not None

    cancel = await unauth_client.post(
        "/api/v1/chat/confirm-action",
        headers=headers,
        json={"action_id": pending["action_id"], "confirmed": False},
    )
    assert cancel.status_code == 200
    assert cancel.json()["executed"] is False

    after = await unauth_client.get("/api/v1/tickets?limit=100", headers=headers)
    assert len(after.json()) == count_before


@pytest.mark.asyncio
async def test_customer_cannot_use_agent_only_routes_after_login(unauth_client: AsyncClient) -> None:
    """RBAC across modules: a logged-in customer is refused on telemetry and ticket deletion."""
    headers = await _login(unauth_client, CUSTOMER_EMAIL)

    usage = await unauth_client.get("/api/v1/agent/ai-usage", headers=headers)
    assert usage.status_code == 403

    created = await unauth_client.post(
        "/api/v1/tickets",
        headers=headers,
        json={
            "customer_name": "Nguyễn Văn An",
            "customer_email": CUSTOMER_EMAIL,
            "category": "General",
            "priority": "Low",
            "subject": "RBAC delete probe",
            "description": "Ticket dùng để kiểm tra quyền xóa.",
        },
    )
    assert created.status_code == 201
    deleted = await unauth_client.delete(f"/api/v1/tickets/{created.json()['id']}", headers=headers)
    assert deleted.status_code == 403


@pytest.mark.asyncio
async def test_protected_flow_rejects_missing_token(unauth_client: AsyncClient) -> None:
    """Without login every step of the flow is refused with HTTP 401 (never a silent success)."""
    assert (await unauth_client.get("/api/v1/tickets")).status_code == 401
    assert (await unauth_client.get("/api/v1/auth/me")).status_code == 401

