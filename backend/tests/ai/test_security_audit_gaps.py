"""Unit tests verifying audit gaps (Task 4):
- Outbound PII redaction happens strictly BEFORE the external LLM call.
- Two-phase confirmation lifecycle (confirm, cancel, double confirmation prevention, cross-user isolation, expiry, unknown ID).
- lookup_customer_tickets tenant & customer isolation (user A cannot see user B's tickets; admin scope).
- Out-of-scope question handling (refusal + escalation + no fabricated citation).
"""

import datetime
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
import pytest_asyncio
from sqlalchemy import select

import app.db.session as session_module
from app.models.ticket import Ticket
from app.models.user import User
from app.schemas.chat import ChatResponse
from app.services.agent_tools import (
    agent_tool_registry,
    handle_lookup_customer_tickets,
    handle_prepare_escalation_ticket,
)
from app.services.llm_service import LLMService
from app.services.rag_service import RAGService


@pytest_asyncio.fixture
async def db_session():
    """Provides an isolated async session for database-dependent unit tests."""
    async with session_module.async_session_factory() as session:
        yield session


@pytest.mark.asyncio
async def test_pii_redaction_happens_strictly_before_llm_call() -> None:
    """
    Task 4: Outbound PII redaction verification:
    Ensure that emails, phone numbers, and citizen IDs are masked BEFORE reaching the LLM SDK.
    """
    captured_contents = None

    class FakeModelsCapturer:
        def generate_content(self, model, contents, config):
            nonlocal captured_contents
            captured_contents = str(contents)
            mock_resp = MagicMock()
            mock_resp.text = "Tôi đã tiếp nhận thông tin bảo hành."
            mock_resp.usage_metadata = MagicMock(prompt_token_count=15, candidates_token_count=10)
            return mock_resp

    service = LLMService()
    service._sdk_type = "genai"
    service.model_name = "gemini-3.5-flash-lite"
    service.api_key = "dummy_key"
    fake_client = MagicMock()
    fake_client.models = FakeModelsCapturer()
    service._client = fake_client

    raw_user_prompt = (
        "Khách hàng Nguyễn Văn An, email: an.secret@company.vn, "
        "số điện thoại: 0912345678, số CCCD: 079198001234 yêu cầu tra cứu bảo hành."
    )

    await service.generate_response(prompt=raw_user_prompt)

    assert captured_contents is not None
    # Raw PII MUST NOT exist in the captured prompt sent to Gemini
    assert "an.secret@company.vn" not in captured_contents
    assert "0912345678" not in captured_contents
    assert "079198001234" not in captured_contents
    # Masked placeholders MUST be present
    assert "[REDACTED_EMAIL]" in captured_contents
    assert "[REDACTED_PHONE]" in captured_contents
    assert "[REDACTED_ID]" in captured_contents


@pytest.mark.asyncio
async def test_confirm_action_full_lifecycle_and_double_confirm_prevention(db_session) -> None:
    """
    Task 4: confirm-action lifecycle:
    1. Propose creates pending action.
    2. Confirm creates exactly one ticket.
    3. Confirming a second time fails and DOES NOT create a second ticket.
    """
    # 1. Propose action
    prep = await handle_prepare_escalation_ticket(
        registry=agent_tool_registry,
        subject="Sự cố mất kết nối mạng văn phòng",
        description="Toàn bộ phòng kinh doanh không truy cập được VPN nội bộ.",
        priority="High",
        category="General",
        customer_email="test.user1@company.vn",
        customer_name="Người Dùng Thử",
        workspace_id=1,
    )
    pending = prep["pending_action"]
    assert pending is not None
    act_id = pending.action_id

    # Count existing tickets
    t_res1 = await db_session.execute(select(Ticket).where(Ticket.customer_email == "test.user1@company.vn"))
    assert len(t_res1.scalars().all()) == 0

    # 2. Confirm action first time -> ticket created
    outcome1 = await agent_tool_registry.execute_pending_action(
        action_id=act_id,
        confirmed=True,
        db=db_session,
    )
    assert outcome1["executed"] is True
    assert outcome1["status"] == "executed"
    created_code = outcome1["ticket_id"]
    assert created_code.startswith("#TICK-")

    # Verify ticket exists in DB
    t_res2 = await db_session.execute(select(Ticket).where(Ticket.ticket_code == created_code))
    created_ticket = t_res2.scalars().first()
    assert created_ticket is not None
    assert created_ticket.subject == "Sự cố mất kết nối mạng văn phòng"

    # 3. Confirming second time must be rejected and must not create a duplicate
    outcome2 = await agent_tool_registry.execute_pending_action(
        action_id=act_id,
        confirmed=True,
        db=db_session,
    )
    assert outcome2["executed"] is False
    assert outcome2["status"] == "already_executed"
    assert outcome2["error_code"] == "ALREADY_EXECUTED"

    # Verify no second ticket was created
    t_res3 = await db_session.execute(select(Ticket).where(Ticket.customer_email == "test.user1@company.vn"))
    assert len(t_res3.scalars().all()) == 1


@pytest.mark.asyncio
async def test_confirm_action_cancel_path(db_session) -> None:
    """
    Task 4: Cancel path: action is marked cancelled and no ticket is written to the DB.
    """
    prep = await handle_prepare_escalation_ticket(
        registry=agent_tool_registry,
        subject="Khách hàng muốn hủy thao tác",
        description="Thử nghiệm hủy bỏ hành động tạo ticket.",
        priority="Low",
        customer_email="cancel.user@company.vn",
        workspace_id=1,
    )
    act_id = prep["pending_action"].action_id

    outcome = await agent_tool_registry.execute_pending_action(
        action_id=act_id,
        confirmed=False,
        db=db_session,
    )
    assert outcome["executed"] is False
    assert outcome["status"] == "cancelled"

    # Verify ticket does not exist
    t_res = await db_session.execute(select(Ticket).where(Ticket.customer_email == "cancel.user@company.vn"))
    assert len(t_res.scalars().all()) == 0


@pytest.mark.asyncio
async def test_confirm_action_cross_user_isolation(db_session) -> None:
    """
    Task 4: User A cannot confirm User B's pending action (RBAC isolation).
    """
    # Create action owned by user A (id=101, email=userA@company.vn)
    user_a = User(id=101, email="userA@company.vn", full_name="User A", role="user")
    user_b = User(id=102, email="userB@company.vn", full_name="User B", role="user")
    admin_user = User(id=1, email="admin@smartdesk.ai", full_name="Admin", role="admin")

    pending = agent_tool_registry.create_pending_action(
        action_type="create_escalation_ticket",
        summary="Action của User A",
        parameters={
            "subject": "Ticket của User A",
            "description": "Chi tiết vấn đề kỹ thuật của User A",
            "priority": "Medium",
            "category": "General",
            "customer_email": "userA@company.vn",
            "customer_name": "User A",
            "workspace_id": 1,
        },
        creator_id=user_a.id,
        creator_email=user_a.email,
    )

    # User B attempts to confirm User A's action -> Forbidden!
    outcome_b = await agent_tool_registry.execute_pending_action(
        action_id=pending.action_id,
        confirmed=True,
        db=db_session,
        current_user=user_b,
    )
    assert outcome_b["executed"] is False
    assert outcome_b["status"] == "forbidden"
    assert outcome_b["error_code"] == "ACTION_FORBIDDEN"

    # Admin CAN confirm User A's action
    outcome_admin = await agent_tool_registry.execute_pending_action(
        action_id=pending.action_id,
        confirmed=True,
        db=db_session,
        current_user=admin_user,
    )
    assert outcome_admin["executed"] is True
    assert outcome_admin["status"] == "executed"


@pytest.mark.asyncio
async def test_confirm_action_unknown_and_expired_id(db_session) -> None:
    """
    Task 4: Unknown action ID returns ACTION_NOT_FOUND; expired ID returns ACTION_EXPIRED.
    """
    # Unknown ID
    unknown_outcome = await agent_tool_registry.execute_pending_action(
        action_id="act-nonexistent-9999",
        confirmed=True,
        db=db_session,
    )
    assert unknown_outcome["executed"] is False
    assert unknown_outcome["status"] == "not_found"
    assert unknown_outcome["error_code"] == "ACTION_NOT_FOUND"

    # Expired ID
    expired_pending = agent_tool_registry.create_pending_action(
        action_type="create_escalation_ticket",
        summary="Expired Action Test",
        parameters={"subject": "Expired", "description": "Expired test"},
    )
    # Manually backdate expires_at
    past_iso = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M:%SZ")
    agent_tool_registry._pending_actions[expired_pending.action_id]["expires_at"] = past_iso

    expired_outcome = await agent_tool_registry.execute_pending_action(
        action_id=expired_pending.action_id,
        confirmed=True,
        db=db_session,
    )
    assert expired_outcome["executed"] is False
    assert expired_outcome["status"] == "expired"
    assert expired_outcome["error_code"] == "ACTION_EXPIRED"


@pytest.mark.asyncio
async def test_lookup_customer_tickets_user_scoping(db_session) -> None:
    """
    Task 4: lookup_customer_tickets scoping:
    User A can never see User B's tickets through chat; Admin can search any ticket.
    """
    # Create two test tickets in DB
    t1 = Ticket(
        ticket_code="#TICK-8001",
        customer_name="User Alpha",
        customer_email="alpha@tenant.vn",
        subject="Vấn đề thanh toán Alpha",
        description="Chi tiết sự cố thanh toán Alpha",
        category="Billing",
        priority="High",
        status="open",
        estimated_response_hours=4,
        workspace_id=1,
    )
    t2 = Ticket(
        ticket_code="#TICK-8002",
        customer_name="User Beta",
        customer_email="beta@tenant.vn",
        subject="Vấn đề bảo mật Beta",
        description="Chi tiết sự cố bảo mật Beta",
        category="Authentication",
        priority="Urgent",
        status="open",
        estimated_response_hours=2,
        workspace_id=1,
    )
    db_session.add(t1)
    db_session.add(t2)
    await db_session.commit()

    user_alpha = User(id=201, email="alpha@tenant.vn", full_name="Alpha", role="user")
    admin_user = User(id=1, email="admin@smartdesk.ai", full_name="Admin", role="admin")

    # 1. User Alpha searches for their own ticket -> Found
    alpha_own = await handle_lookup_customer_tickets(
        session=db_session,
        ticket_code="#TICK-8001",
        current_user=user_alpha,
    )
    assert alpha_own["found"] is True
    assert "#TICK-8001" in alpha_own["message"]

    # 2. User Alpha searches for User Beta's ticket -> NOT Found (forbidden access)
    alpha_lookup_beta = await handle_lookup_customer_tickets(
        session=db_session,
        ticket_code="#TICK-8002",
        current_user=user_alpha,
    )
    assert alpha_lookup_beta["found"] is False
    assert "Không tìm thấy" in alpha_lookup_beta["message"]
    assert "#TICK-8002" not in alpha_lookup_beta.get("tickets", [])

    # 3. Admin searches for User Beta's ticket -> Found (Admin privilege)
    admin_lookup_beta = await handle_lookup_customer_tickets(
        session=db_session,
        ticket_code="#TICK-8002",
        current_user=admin_user,
    )
    assert admin_lookup_beta["found"] is True
    assert "#TICK-8002" in admin_lookup_beta["message"]


@pytest.mark.asyncio
async def test_out_of_scope_query_refusal_and_no_fabricated_citations() -> None:
    """
    Task 4: Out-of-scope query behavior:
    1. Returns polite refusal with escalation recommended.
    2. Citations must be EMPTY (no fabricated citation claiming to support the answer).
    """
    rag = RAGService()
    mock_llm = MagicMock()
    mock_llm.is_in_cooldown.return_value = False
    mock_llm.is_available.return_value = True
    mock_llm.provider = "gemini"
    mock_llm.active_model_name = "gemini-3.5-flash-lite"
    mock_llm.last_input_tokens = 25
    mock_llm.last_output_tokens = 30
    mock_llm.last_cost_usd = 0.0001
    mock_llm.generate_response = AsyncMock(
        return_value=(
            "Xin lỗi quý khách, câu hỏi về cách nấu phở bò không thuộc phạm vi hỗ trợ của hệ thống. "
            "Quý khách vui lòng liên hệ bộ phận hỗ trợ hoặc gửi ticket nếu cần trợ giúp về dịch vụ đám mây.",
            450.0
        )
    )

    with patch("app.services.rag_service.llm_service", mock_llm):
        with patch.object(rag, "retrieve_context_documents", new_callable=AsyncMock) as mock_ret:
            # Out-of-scope query yields no relevant knowledge chunks
            mock_ret.return_value = []
            res: ChatResponse = await rag.answer_query(
                query="Hướng dẫn tôi cách nấu phở bò gia truyền Hà Nội ngon chuẩn vị?",
                workspace_id=1,
            )
            assert res.escalation_recommended is True
            assert res.confidence < 0.65
            # Citations MUST be empty (never fabricate citations for out-of-scope queries)
            assert len(res.citations) == 0
            assert "phở" in res.response.lower()
