"""Dedicated module test suite for Owner 2 (Tickets, SLA Calculation & Canonical Categories)."""

import sys
from pathlib import Path
import pytest
from httpx import AsyncClient

backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.schemas.ticket import CANONICAL_TICKET_CATEGORIES, TicketCategoryEnum, TicketPriorityEnum
from app.services.ticket_service import ticket_service


def test_canonical_sla_hours_mapping() -> None:
    """Verify SLA hours match the frozen contract (Urgent=2, High=4, Medium=8, Low=24)."""
    assert ticket_service.calculate_sla_hours("Urgent") == 2
    assert ticket_service.calculate_sla_hours("High") == 4
    assert ticket_service.calculate_sla_hours("Medium") == 8
    assert ticket_service.calculate_sla_hours("Low") == 24


def test_canonical_ticket_categories_and_alias() -> None:
    """Verify both Bug Report (canonical) and Technical Bug (alias) are supported."""
    assert "Bug Report" in CANONICAL_TICKET_CATEGORIES
    assert TicketCategoryEnum.BUG_REPORT.value == "Bug Report"
    assert TicketCategoryEnum.TECHNICAL_BUG.value == "Technical Bug"
    assert TicketPriorityEnum.URGENT.value == "Urgent"


# =========================================================================
# Task B2 Tests: Server-side Sorting, X-Total-Count Header, Delete API (REQ-15, REQ-30, REQ-31)
# =========================================================================

@pytest.mark.asyncio
async def test_ticket_server_side_sorting_and_total_count_header(admin_client: AsyncClient) -> None:
    """Verify GET /api/v1/tickets returns X-Total-Count header and supports sort_by / sort_order."""
    # 1. Query with pagination and sorting
    res = await admin_client.get("/api/v1/tickets?sort_by=created_at&sort_order=desc&limit=5")
    assert res.status_code == 200
    assert "x-total-count" in res.headers
    total_count = int(res.headers["x-total-count"])
    assert total_count >= 1

    tickets = res.json()
    assert isinstance(tickets, list)
    assert len(tickets) <= 5

    # 2. Query sorted by priority asc
    res_prio = await admin_client.get("/api/v1/tickets?sort_by=priority&sort_order=asc")
    assert res_prio.status_code == 200
    assert "x-total-count" in res_prio.headers


@pytest.mark.asyncio
async def test_workspace_delete_rules(admin_client: AsyncClient) -> None:
    """Verify DELETE /api/v1/workspaces blocks deleting default ID=1 and permits custom workspaces."""
    # 1. Attempt to delete default workspace (ID=1) -> HTTP 400 Bad Request
    res_del_default = await admin_client.delete("/api/v1/workspaces/1")
    assert res_del_default.status_code == 400
    assert "Không thể xóa Workspace mặc định" in res_del_default.json()["detail"]

    # 2. Create a temporary custom workspace
    ws_create = await admin_client.post(
        "/api/v1/workspaces",
        json={
            "slug": "temp-test-ws",
            "name": "Temporary Test Workspace",
            "industry": "Testing",
            "persona_name": "Test Bot",
            "tone_of_voice": "Friendly",
            "business_rules": "No special rules."
        }
    )
    assert ws_create.status_code == 201
    custom_ws_id = ws_create.json()["id"]

    # 3. Delete the custom workspace -> HTTP 204 No Content
    res_del_custom = await admin_client.delete(f"/api/v1/workspaces/{custom_ws_id}")
    assert res_del_custom.status_code == 204

    # 4. Verify it no longer exists -> HTTP 404
    res_get = await admin_client.get(f"/api/v1/workspaces/{custom_ws_id}")
    assert res_get.status_code == 404


@pytest.mark.asyncio
async def test_ticket_creation_integrates_copilot_service(admin_client: AsyncClient) -> None:
    """Verify TicketService integrates single-call Copilot triage to produce tags and draft reply."""
    res = await admin_client.post(
        "/api/v1/tickets",
        json={
            "customer_name": "Hoàng Minh Trí",
            "customer_email": "tri.hoang@company.vn",
            "category": "Authentication",
            "priority": "High",
            "subject": "Không nhận được mã OTP qua SMS",
            "description": "Tôi đã yêu cầu gửi lại OTP 3 lần nhưng không nhận được tin nhắn."
        }
    )
    assert res.status_code == 201
    data = res.json()
    assert data["ticket_code"].startswith("#TICK-")
    assert "Authentication" in data["ai_tags"]
    assert data["ai_draft_reply"] is not None
    assert len(data["ai_draft_reply"]) > 20
