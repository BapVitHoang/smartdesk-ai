"""Tests for LLM-driven tool selection (Capability B) and provider-level SSE token streaming (REQ-04, REQ-10)."""

import json
from typing import Any, Callable, Optional
from unittest.mock import AsyncMock, patch

import pytest

from app.models.user import User
from app.schemas.chat import ChatResponse
from app.services.agent_tools import (
    AgentToolRegistry,
    detect_and_route_tool,
    register_default_tools,
)
from app.services.llm_service import llm_service
from app.services.rag_service import rag_service

ADMIN = User(id=1, email="admin@smartdesk.ai", role="admin", full_name="Admin Staff")
CUSTOMER = User(
    id=2, email="an.nguyen@company.vn", role="user", full_name="Nguyễn Văn An"
)


@pytest.fixture
def registry() -> AgentToolRegistry:
    reg = AgentToolRegistry()
    register_default_tools(reg)
    return reg


def _llm_online(selection: Any = None, error: Optional[Exception] = None):
    select_mock = AsyncMock(return_value=selection, side_effect=error)
    return (
        patch.object(llm_service, "is_available", return_value=True),
        patch.object(llm_service, "is_in_cooldown", return_value=False),
        patch.object(llm_service, "select_tool", select_mock),
        select_mock,
    )


@pytest.mark.asyncio
async def test_llm_selects_tool_and_receives_all_four_declarations(registry):
    p1, p2, p3, select_mock = _llm_online(
        {"name": "lookup_customer_tickets", "args": {}}
    )
    with p1, p2, p3:
        info: dict = {}
        result = await detect_and_route_tool(
            "Phiếu #TICK-1042 của tôi tới đâu rồi?",
            registry=registry,
            current_user=CUSTOMER,
            routing_info=info,
        )
    assert info["router"] == "llm"
    assert result["tool_router"] == "llm"
    assert result["tools_called"] == ["lookup_customer_tickets"]
    tools_sent = select_mock.await_args.args[1]
    assert {t["name"] for t in tools_sent} == {
        "lookup_customer_tickets",
        "search_workspace_knowledge",
        "create_escalation_ticket",
        "update_ticket_priority_or_status",
    }


@pytest.mark.asyncio
async def test_llm_choosing_no_tool_routes_to_rag_even_if_keywords_match(registry):
    p1, p2, p3, _ = _llm_online(None)
    with p1, p2, p3:
        result = await detect_and_route_tool(
            "Tạo ticket mới giúp tôi được không, phí là bao nhiêu?", registry=registry
        )
    assert result is None


@pytest.mark.asyncio
async def test_llm_failure_falls_back_to_keyword_router(registry):
    p1, p2, p3, _ = _llm_online(error=RuntimeError("upstream 503"))
    with p1, p2, p3:
        info: dict = {}
        result = await detect_and_route_tool(
            "Tạo giúp tôi một ticket về lỗi đăng nhập",
            registry=registry,
            current_user=CUSTOMER,
            routing_info=info,
        )
    assert info["router"] == "rules"
    assert result["tools_called"] == ["create_escalation_ticket"]
    assert result["pending_action"] is not None


@pytest.mark.asyncio
async def test_keyword_router_understands_ui_term_yeu_cau_ho_tro(registry):
    with patch.object(llm_service, "is_available", return_value=False):
        result = await detect_and_route_tool(
            "Tạo giúp tôi một yêu cầu hỗ trợ về lỗi đăng nhập sau khi đổi mật khẩu",
            registry=registry,
            current_user=CUSTOMER,
        )
    assert result["tools_called"] == ["create_escalation_ticket"]
    assert result["pending_action"].requires_confirmation is True


@pytest.mark.asyncio
async def test_llm_create_ticket_requires_confirmation_and_ignores_hallucinated_email(
    registry,
):
    selection = {
        "name": "create_escalation_ticket",
        "args": {
            "subject": "Không đăng nhập được",
            "description": "Khách báo lỗi đăng nhập sau khi đổi mật khẩu",
            "priority": "High",
            "category": "Authentication",
            "customer_email": "attacker@evil.example",
        },
    }
    p1, p2, p3, _ = _llm_online(selection)
    with p1, p2, p3:
        result = await detect_and_route_tool(
            "Mình không đăng nhập được, tạo yêu cầu hỗ trợ giúp",
            registry=registry,
            current_user=CUSTOMER,
        )
    pending = result["pending_action"]
    assert pending is not None and pending.requires_confirmation is True
    assert pending.parameters["customer_email"] == CUSTOMER.email
    assert pending.parameters["priority"] == "High"
    assert pending.parameters["category"] == "Authentication"


@pytest.mark.asyncio
async def test_llm_update_by_customer_is_refused_from_prompt_catalog(registry):
    selection = {
        "name": "update_ticket_priority_or_status",
        "args": {"priority": "Urgent"},
    }
    p1, p2, p3, _ = _llm_online(selection)
    with p1, p2, p3:
        result = await detect_and_route_tool(
            "Đổi #TICK-1042 sang khẩn cấp", registry=registry, current_user=CUSTOMER
        )
    assert result["pending_action"] is None
    assert "Quản trị viên" in result["response"]


@pytest.mark.asyncio
async def test_llm_update_by_admin_prepares_pending_action(registry):
    selection = {
        "name": "update_ticket_priority_or_status",
        "args": {"priority": "urgent", "status": "in_progress"},
    }
    p1, p2, p3, _ = _llm_online(selection)
    with p1, p2, p3:
        result = await detect_and_route_tool(
            "Nâng #TICK-1042 lên Urgent", registry=registry, current_user=ADMIN
        )
    params = result["pending_action"].parameters
    assert params == {
        "ticket_code": "#TICK-1042",
        "priority": "Urgent",
        "status": "in_progress",
    }


@pytest.mark.asyncio
async def test_generate_response_stream_relays_provider_chunks():
    async def fake_stream(
        prompt: str,
        system_prompt: Any,
        temperature: float,
        on_token: Callable[[str], None],
    ):
        for piece in ["Xin ", "chào ", "bạn"]:
            on_token(piece)
        return "Xin chào bạn", 12.0

    with patch.object(llm_service, "stream_generate", side_effect=fake_stream):
        chunks = [c async for c in llm_service.generate_response_stream("hi")]
    assert chunks == ["Xin ", "chào ", "bạn"]


@pytest.mark.asyncio
async def test_answer_query_stream_forwards_live_tokens_without_resplitting():
    async def fake_answer(
        query: str, session=None, workspace_id=None, current_user=None, token_sink=None
    ):
        token_sink("Chính sách ")
        token_sink("đổi trả 30 ngày.")
        return ChatResponse(
            response="Chính sách đổi trả 30 ngày.", latency_ms=5.0, confidence=0.9
        )

    with patch.object(rag_service, "answer_query", side_effect=fake_answer):
        events = [e async for e in rag_service.answer_query_stream("đổi trả?")]

    payloads = [json.loads(e.split("data: ", 1)[1]) for e in events]
    assert payloads[0]["type"] == "metadata"
    assert [p["token"] for p in payloads if p["type"] == "token"] == [
        "Chính sách ",
        "đổi trả 30 ngày.",
    ]
    assert payloads[-1]["type"] == "done"
    assert payloads[-1]["response"] == "Chính sách đổi trả 30 ngày."
