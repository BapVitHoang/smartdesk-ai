"""Dedicated module test suite for Owner 1 (AI, RAG, Prompt Registry & Agent Tools)."""

import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.core.prompts import prompt_registry
from app.services.agent_tools import AgentToolRegistry, ToolDefinition
from app.services.fallback_service import fallback_service


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


def test_agent_tool_registry_registration() -> None:
    """Verify AgentToolRegistry registers and serializes tool definitions cleanly."""
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
