"""Offline test suite for ticket creation authentication and tenant isolation (REQ-SEC-03)."""

import pytest
from httpx import AsyncClient

from app.core.config import settings


@pytest.mark.asyncio
async def test_ticket_creation_unauthenticated_returns_401(unauth_client: AsyncClient) -> None:
    """Verify unauthenticated visitor cannot submit a support ticket (HTTP 401)."""
    payload = {
        "customer_name": "Anonymous Visitor",
        "customer_email": "visitor@example.com",
        "category": "General",
        "priority": "Low",
        "subject": "Cần hỗ trợ về tài khoản",
        "description": "Tôi không thể truy cập tài khoản của mình.",
    }
    res = await unauth_client.post("/api/v1/tickets", json=payload)
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_ticket_creation_authenticated_user_binds_to_token_and_sees_ticket(
    unauth_client: AsyncClient,
) -> None:
    """Verify authenticated user can create ticket and the ticket owner is strictly bound to token."""
    # 1. Login as regular user (an.nguyen@company.vn)
    login_res = await unauth_client.post(
        "/api/v1/auth/token",
        json={"username": "an.nguyen@company.vn", "password": settings.DEMO_USER_PASSWORD},
    )
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    user_headers = {"Authorization": f"Bearer {token}"}

    # 2. Submit ticket with body attempting to forge another customer's email
    payload = {
        "customer_name": "Attacker Spoofed Name",
        "customer_email": "victim@othercompany.vn",
        "category": "Bug Report",
        "priority": "Medium",
        "subject": "Lỗi đồng bộ dữ liệu giao dịch",
        "description": "Dữ liệu giao dịch không cập nhật sau khi thanh toán.",
    }
    create_res = await unauth_client.post("/api/v1/tickets", json=payload, headers=user_headers)
    assert create_res.status_code == 201
    ticket = create_res.json()

    # Assert customer_email was strictly locked to token owner, NOT the body
    assert ticket["customer_email"] == "an.nguyen@company.vn"
    assert ticket["customer_name"] == "Nguyễn Văn An"

    # 3. User can see the created ticket in their ticket list
    list_res = await unauth_client.get("/api/v1/tickets", headers=user_headers)
    assert list_res.status_code == 200
    ticket_ids = [t["id"] for t in list_res.json()]
    assert ticket["id"] in ticket_ids


@pytest.mark.asyncio
async def test_ticket_creation_admin_can_specify_customer_details(unauth_client: AsyncClient) -> None:
    """Verify support staff/admin can create a ticket on behalf of a specific customer."""
    # 1. Login as admin
    login_res = await unauth_client.post(
        "/api/v1/auth/token",
        json={"username": "admin@smartdesk.ai", "password": settings.DEMO_ADMIN_PASSWORD},
    )
    assert login_res.status_code == 200
    admin_token = login_res.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # 2. Admin submits ticket on behalf of a corporate customer
    customer_email = "corporate.client@enterprise.vn"
    customer_name = "Trần Doanh Nghiệp"
    payload = {
        "customer_name": customer_name,
        "customer_email": customer_email,
        "category": "Billing",
        "priority": "High",
        "subject": "Yêu cầu xuất hóa đơn điện tử VAT",
        "description": "Vui lòng xuất hóa đơn VAT cho hợp đồng doanh nghiệp tháng 10.",
    }
    create_res = await unauth_client.post("/api/v1/tickets", json=payload, headers=admin_headers)
    assert create_res.status_code == 201
    ticket = create_res.json()

    # Admin's specified customer details are preserved
    assert ticket["customer_email"] == customer_email
    assert ticket["customer_name"] == customer_name

