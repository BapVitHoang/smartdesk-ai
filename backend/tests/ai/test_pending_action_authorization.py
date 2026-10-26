"""
Tests for Two-Phase Agent Action Authorization and Privilege Escalation Defense (MRG-DEF-06 / Capability B).

Enforces Decision Option A:
Only admins may change ticket status or priority through chat (mutating tool update_ticket_priority_or_status).
Regular customers and unauthenticated users receive a polite Vietnamese refusal and no pending action.
Enforced at PREPARE time and again at EXECUTE time (defense in depth).
"""

import pytest
import pytest_asyncio
from unittest.mock import MagicMock
from sqlalchemy import select

import app.db.session as session_module
from app.models.ticket import Ticket
from app.models.user import User
from app.services.agent_tools import (
    AgentToolRegistry,
    detect_and_route_tool,
    register_default_tools,
)


@pytest_asyncio.fixture
async def db_session():
    """Provides an isolated async session for database-dependent unit tests."""
    async with session_module.async_session_factory() as session:
        yield session


@pytest.fixture
def clean_registry():
    """Provides a fresh isolated tool registry."""
    reg = AgentToolRegistry()
    register_default_tools(reg)
    return reg


@pytest.mark.asyncio
async def test_normal_user_cannot_prepare_ticket_update(clean_registry, db_session):
    """
    Test 1: A normal customer (role='user') asks to update a ticket.
    Must be rejected at PREPARE time with a polite refusal and NO pending action.
    """
    normal_user = User(id=2, email="an.nguyen@company.vn", role="user", full_name="Nguyen Van An")
    query = "Vui lòng cập nhật ticket #TICK-1042 mức độ ưu tiên khẩn cấp Urgent"

    result = await detect_and_route_tool(
        query=query,
        session=db_session,
        registry=clean_registry,
        current_user=normal_user,
    )

    assert result is not None
    assert result["pending_action"] is None, "Regular users must NEVER receive a pending_action to update ticket status/priority."
    assert "Quản trị viên" in result["response"] or "Admin" in result["response"]
    assert "hỗ trợ" in result["response"].lower()


@pytest.mark.asyncio
async def test_unauthenticated_user_cannot_prepare_ticket_update(clean_registry, db_session):
    """
    Test 2: An unauthenticated caller (current_user=None) asks to update a ticket.
    Must fail closed at PREPARE time with NO pending action.
    """
    query = "Cập nhật ticket #TICK-1042 sang resolved"

    result = await detect_and_route_tool(
        query=query,
        session=db_session,
        registry=clean_registry,
        current_user=None,
    )

    assert result is not None
    assert result["pending_action"] is None, "Unauthenticated callers must NEVER receive a pending_action to update ticket."
    assert "Quản trị viên" in result["response"] or "Admin" in result["response"]


@pytest.mark.asyncio
async def test_admin_can_prepare_ticket_update_with_creator_metadata(clean_registry, db_session):
    """
    Test 3: An admin user (role='admin') asks to update a ticket.
    Succeeds at PREPARE time: creates pending action storing creator_id and creator_email.
    """
    admin_user = User(id=1, email="admin@smartdesk.ai", role="admin", full_name="Admin Staff")
    query = "Cập nhật ticket #TICK-1042 mức độ ưu tiên High"

    result = await detect_and_route_tool(
        query=query,
        session=db_session,
        registry=clean_registry,
        current_user=admin_user,
    )

    assert result is not None
    pending = result["pending_action"]
    assert pending is not None
    assert pending.action_type == "update_ticket_priority_or_status"

    stored = clean_registry.get_pending_action(pending.action_id)
    assert stored is not None
    assert stored.get("creator_id") == 1
    assert stored.get("creator_email") == "admin@smartdesk.ai"


@pytest.mark.asyncio
async def test_execute_pending_update_rejects_non_admin_and_preserves_db(clean_registry, db_session):
    """
    Test 4 (CRITICAL VULNERABILITY CHECK):
    Even if an update action was prepared, a non-admin attempting to EXECUTE it
    must be rejected with ACTION_FORBIDDEN and the database ticket must NOT be mutated.
    """
    # Seed a test ticket if not exists
    res = await db_session.execute(select(Ticket).where(Ticket.ticket_code == "#TICK-1042"))
    t = res.scalars().first()
    if not t:
        t = Ticket(
            ticket_code="#TICK-1042",
            workspace_id=1,
            customer_name="Customer",
            customer_email="customer@example.com",
            category="General",
            priority="Low",
            status="open",
            subject="Test ticket",
            description="Test ticket body",
        )
        db_session.add(t)
        await db_session.commit()
        await db_session.refresh(t)

    original_priority = t.priority
    original_status = t.status

    # Manually store a pending action
    action = clean_registry.create_pending_action(
        action_type="update_ticket_priority_or_status",
        summary="Cập nhật #TICK-1042: Ưu tiên -> Urgent",
        parameters={"ticket_code": "#TICK-1042", "priority": "Urgent", "status": "resolved"},
        creator_id=1,
        creator_email="admin@smartdesk.ai",
    )

    # Attacker tries to confirm it
    attacker = User(id=99, email="attacker@evil.com", role="user")
    outcome = await clean_registry.execute_pending_action(
        action_id=action.action_id,
        confirmed=True,
        db=db_session,
        current_user=attacker,
    )

    assert outcome["executed"] is False
    assert outcome["status"] == "forbidden"
    assert outcome.get("error_code") == "ACTION_FORBIDDEN"

    # Verify ticket in database was NOT changed
    await db_session.refresh(t)
    assert t.priority == original_priority, "Ticket priority was mutated by unauthorized user!"
    assert t.status == original_status, "Ticket status was mutated by unauthorized user!"


@pytest.mark.asyncio
async def test_pending_action_cannot_be_confirmed_by_different_user(clean_registry, db_session):
    """
    Test 5: An escalation ticket action created by User X cannot be confirmed by User Y.
    """
    action = clean_registry.create_pending_action(
        action_type="create_escalation_ticket",
        summary="Tạo ticket mẫu",
        parameters={"subject": "Sự cố", "description": "Mô tả", "customer_name": "User X"},
        creator_id=10,
        creator_email="userx@company.vn",
    )

    user_y = User(id=20, email="usery@company.vn", role="user")
    outcome = await clean_registry.execute_pending_action(
        action_id=action.action_id,
        confirmed=True,
        db=db_session,
        current_user=user_y,
    )

    assert outcome["executed"] is False
    assert outcome["status"] == "forbidden"
    assert outcome.get("error_code") == "ACTION_FORBIDDEN"


@pytest.mark.asyncio
async def test_tampered_or_unknown_action_id_rejected(clean_registry, db_session):
    """
    Test 6: Confirming a non-existent or tampered action ID returns not_found.
    """
    outcome = await clean_registry.execute_pending_action(
        action_id="act-nonexistent-123",
        confirmed=True,
        db=db_session,
        current_user=User(id=1, email="admin@smartdesk.ai", role="admin"),
    )

    assert outcome["executed"] is False
    assert outcome["status"] == "not_found"
    assert outcome.get("error_code") == "ACTION_NOT_FOUND"


@pytest.mark.asyncio
async def test_cancellation_path_does_not_mutate_ticket(clean_registry, db_session):
    """
    Test 7: When user clicks 'Hủy bỏ' (confirmed=False), action is cancelled and DB is untouched.
    """
    res = await db_session.execute(select(Ticket).where(Ticket.ticket_code == "#TICK-1042"))
    t = res.scalars().first()
    original_prio = t.priority if t else "Low"

    action = clean_registry.create_pending_action(
        action_type="update_ticket_priority_or_status",
        summary="Cập nhật #TICK-1042",
        parameters={"ticket_code": "#TICK-1042", "priority": "Urgent"},
        creator_id=1,
        creator_email="admin@smartdesk.ai",
    )

    admin = User(id=1, email="admin@smartdesk.ai", role="admin")
    outcome = await clean_registry.execute_pending_action(
        action_id=action.action_id,
        confirmed=False,
        db=db_session,
        current_user=admin,
    )

    assert outcome["executed"] is False
    assert outcome["status"] == "cancelled"

    if t:
        await db_session.refresh(t)
        assert t.priority == original_prio
