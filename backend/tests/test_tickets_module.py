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


@pytest.mark.asyncio
async def test_demo_tickets_pagination_and_sorting(admin_client: AsyncClient) -> None:
    """Verify pagination (?page=2) and sorting with 40+ seeded demo tickets."""
    # 1. Page 1 vs Page 2 with limit=10
    res_page1 = await admin_client.get("/api/v1/tickets?sort_by=created_at&sort_order=desc&limit=10&page=1")
    assert res_page1.status_code == 200
    total_count = int(res_page1.headers.get("x-total-count", "0"))
    assert total_count >= 40, f"Expected at least 40 tickets, got {total_count}"

    tickets_p1 = res_page1.json()
    assert len(tickets_p1) == 10
    p1_codes = [t["ticket_code"] for t in tickets_p1]

    res_page2 = await admin_client.get("/api/v1/tickets?sort_by=created_at&sort_order=desc&limit=10&page=2")
    assert res_page2.status_code == 200
    tickets_p2 = res_page2.json()
    assert len(tickets_p2) == 10
    p2_codes = [t["ticket_code"] for t in tickets_p2]

    # Verify page 2 returns distinct rows from page 1
    assert set(p1_codes).isdisjoint(set(p2_codes)), "Page 1 and Page 2 rows must not overlap!"

    # 2. Verify sorting by priority (Urgent=1 -> High=2 -> Medium=3 -> Low=4)
    res_prio_asc = await admin_client.get("/api/v1/tickets?sort_by=priority&sort_order=asc&limit=10&page=1")
    assert res_prio_asc.status_code == 200
    prio_asc_tickets = res_prio_asc.json()
    assert len(prio_asc_tickets) == 10
    # First items in asc must be Urgent
    assert prio_asc_tickets[0]["priority"] == "Urgent"

    res_prio_desc = await admin_client.get("/api/v1/tickets?sort_by=priority&sort_order=desc&limit=10&page=1")
    assert res_prio_desc.status_code == 200
    prio_desc_tickets = res_prio_desc.json()
    assert len(prio_desc_tickets) == 10
    # First items in desc must be Low
    assert prio_desc_tickets[0]["priority"] == "Low"


@pytest.mark.asyncio
async def test_demo_tickets_user_isolation(admin_client: AsyncClient, user_client: AsyncClient) -> None:
    """Verify regular user (an.nguyen@company.vn) only sees their own tickets among 40+ demo tickets."""
    # Admin sees all tickets (>= 40)
    res_admin = await admin_client.get("/api/v1/tickets?limit=100")
    assert res_admin.status_code == 200
    admin_total = int(res_admin.headers.get("x-total-count", "0"))
    assert admin_total >= 40

    # User only sees tickets assigned to an.nguyen@company.vn (15 tickets)
    res_user = await user_client.get("/api/v1/tickets?limit=100")
    assert res_user.status_code == 200
    user_total = int(res_user.headers.get("x-total-count", "0"))
    assert user_total < admin_total
    assert user_total >= 14, f"Expected An Nguyen to have at least 14 tickets, got {user_total}"

    user_tickets = res_user.json()
    assert len(user_tickets) == user_total
    for t in user_tickets:
        assert t["customer_email"] == "an.nguyen@company.vn"

