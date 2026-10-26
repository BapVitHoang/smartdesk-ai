"""Dedicated module test suite for Owner 1 / Dev A (AI, RAG, Structured Output, SSE Streaming, Prompt Registry & Agent Tools)."""

import sys
from pathlib import Path
import pytest

backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.core.prompts import prompt_registry
from app.schemas.ai_structured import (
    AgentHandOffStep,
    FaithfulnessJudgeStructuredOutput,
    TicketCopilotStructuredOutput,
)
from app.services.agent_tools import (
    AgentToolRegistry,
    ToolDefinition,
    agent_tool_registry,
    detect_and_route_tool,
)
from app.services.fallback_service import fallback_service
from app.services.ticket_copilot_service import generate_ticket_triage_and_draft
from app.services.verification_service import verification_service


def test_prompt_registry_loads_versioned_templates() -> None:
    """Verify externalized prompts.json loads with version and renders variables."""
    assert prompt_registry.version == "1.0.0"
    rendered = prompt_registry.render(
        "rag_customer_support",
        persona_name="SmartDesk Bot",
        workspace_name="SmartDesk Cloud",
        industry="SaaS",
        tone_of_voice="Professional",
        business_rules="Always cite sources.",
    )
    assert "SmartDesk Bot" in rendered
    assert "SmartDesk Cloud" in rendered
    assert prompt_registry.get_prompt_version("rag_customer_support").startswith("rag_customer_support@v")


def test_agent_tool_registry_registration_and_default_tools() -> None:
    """Verify AgentToolRegistry registers custom tools and comes pre-loaded with 4 default tools."""
    registry = AgentToolRegistry()
    registry.register(
        ToolDefinition(
            name="lookup_ticket_status",
            description="Look up ticket status by #TICK-XXXX code.",
            parameters_schema={"type": "object", "properties": {"ticket_code": {"type": "string"}}},
            requires_confirmation=False,
        )
    )
    tools = registry.list_tools()
    assert len(tools) == 1
    assert tools[0]["name"] == "lookup_ticket_status"

    # Verify global agent_tool_registry has all 4 required tools (REQ-14)
    default_names = {t["name"] for t in agent_tool_registry.list_tools()}
    assert {
        "lookup_customer_tickets",
        "search_workspace_knowledge",
        "create_escalation_ticket",
        "update_ticket_priority_or_status",
    }.issubset(default_names)


def test_bm25_fallback_deterministic_match() -> None:
    """Verify BM25 fallback returns grounded FAQ citation with is_fallback=True."""
    result = fallback_service.match_faq("How do I reset my password and 2FA?")
    assert result["is_fallback"] is True
    assert isinstance(result["citations"], list)
    assert len(result["citations"]) >= 1


def test_bm25_fallback_with_custom_chunks_workspace_2() -> None:
    """Verify BM25 fallback matches custom published chunks for Workspace 2."""
    custom_chunks = [
        {
            "doc_id": "doc-2-chk-1",
            "title": "Bảng giá nha khoa SmileCare",
            "content": "Dịch vụ tẩy trắng răng Laser Whitening trọn gói 2.500.000 VNĐ.",
            "source_url": "/workspaces/2/docs/1"
        }
    ]
    res = fallback_service.match_faq(
        query="Chi phí tẩy trắng răng bao nhiêu?",
        workspace_id=2,
        workspace_name="Nha Khoa SmileCare",
        docs=custom_chunks
    )
    assert res["is_fallback"] is True
    assert "tẩy trắng răng" in res["response"].lower()
    assert res["citations"][0]["doc_id"] == "doc-2-chk-1"


def test_structured_output_schemas_and_category_alias_normalization() -> None:
    """Verify TicketCopilotStructuredOutput normalizes 'Technical Bug' alias to 'Bug Report' (CONTRACTS.md §4)."""
    output = TicketCopilotStructuredOutput(
        category="Technical Bug",  # type: ignore[arg-type]
        priority="High",
        ai_tags=["SSO", "403 Forbidden"],
        sentiment="frustrated",
        summary="Khách hàng gặp lỗi 403 khi đăng nhập SSO Google.",
        ai_draft_reply="Kính gửi quý khách, chúng tôi đang kiểm tra cấu hình SSO SAML 2.0 của quý khách.",
    )
    assert output.category == "Bug Report"
    assert output.priority == "High"

    judge = FaithfulnessJudgeStructuredOutput(
        score=0.95,
        status="passed",
        reason="Câu trả lời chính xác tuyệt đối với tài liệu gốc.",
        missing_facts=[],
    )
    assert judge.score == 0.95
    assert judge.status == "passed"


@pytest.mark.asyncio
async def test_ticket_copilot_service_single_call_fallback() -> None:
    """Verify generate_ticket_triage_and_draft produces validated structured output even when offline."""
    result = await generate_ticket_triage_and_draft(
        subject="Lỗi thanh toán VNPAY bị trừ tiền 2 lần",
        description="Tôi thanh toán hóa đơn qua cổng VNPAY bị trừ tiền 2 lần, yêu cầu hoàn tiền gấp!",
        workspace_id=1,
        customer_name="Nguyễn Văn An",
    )
    assert isinstance(result, TicketCopilotStructuredOutput)
    assert result.category == "Billing"
    assert len(result.ai_tags) >= 1
    assert "Nguyễn Văn An" in result.ai_draft_reply


@pytest.mark.asyncio
async def test_agent_tool_router_creates_pending_confirmation_for_mutating_actions() -> None:
    """Verify mutating tool requests create a PendingAction requiring explicit user confirmation."""
    create_route = await detect_and_route_tool(
        query="Tạo giúp tôi ticket lỗi VNPAY mức Urgent",
        session=None,
        workspace_id=1,
    )
    assert create_route is not None
    assert "create_escalation_ticket" in create_route["tools_called"]
    pending = create_route["pending_action"]
    assert pending is not None
    assert pending.requires_confirmation is True
    assert pending.action_type == "create_escalation_ticket"
    assert pending.action_id.startswith("act-")

    # Verify cancelling the pending action does not execute
    cancel_res = await agent_tool_registry.execute_pending_action(
        action_id=pending.action_id,
        confirmed=False,
        db=None,
    )
    assert cancel_res["executed"] is False
    assert cancel_res["status"] == "cancelled"


def test_verification_service_multi_agent_trace_generation() -> None:
    """Verify VerificationService returns 3-step multi-agent hand-off trace (Capability E - REQ-17)."""
    trace = verification_service.get_agent_trace(document_id=99, faithfulness_score=0.94, status="passed", item_count=3)
    assert len(trace) == 3
    assert isinstance(trace[0], AgentHandOffStep)
    assert [step.agent for step in trace] == [
        "SyntheticQAExamAgent",
        "SandboxRAGAgent",
        "FaithfulnessJudgeAgent",
    ]
