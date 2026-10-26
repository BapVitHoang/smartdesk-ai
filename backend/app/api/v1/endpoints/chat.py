"""Chat endpoint handling customer RAG inquiries with guardrail refusal logging and automatic fallback."""

import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.endpoints.chat_actions import get_optional_current_user
from app.core.exceptions import InvalidPromptException
from app.core.prompts import prompt_registry
from app.core.security import check_prompt_injection, sanitize_input
from app.db.session import get_db
from app.models.user import User
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.ai_usage_logger import log_ai_call
from app.services.llm_service import llm_service
from app.services.rag_service import rag_service

logger = logging.getLogger("smartdesk.api.chat")

router = APIRouter()


@router.post(
    "",
    response_model=ChatResponse,
    status_code=status.HTTP_200_OK,
    summary="Customer AI Assistant RAG Query",
    description=(
        "Processes customer inquiries using Google Gemini 3.5 Flash Lite / Ollama grounded on verified knowledge documents. "
        "Returns structured citations, tool calls, pending confirmation cards, and latency. Automatically trips circuit breaker to FallbackService on failure."
    )
)
async def chat_with_assistant(
    payload: ChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
) -> ChatResponse:
    """Customer chat endpoint supporting RAG grounding, tool calling, and graceful fallback."""
    cleaned_message = sanitize_input(payload.message)
    if not cleaned_message:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Message content cannot be empty after sanitization."
        )

    is_suspicious, reason = check_prompt_injection(cleaned_message)
    if is_suspicious:
        logger.warning(f"Rejected malicious prompt: {reason}")
        await log_ai_call(
            endpoint="/api/v1/chat",
            prompt_version=prompt_registry.get_prompt_version("rag_customer_support"),
            provider="guardrail",
            model_name=llm_service.active_model_name,
            tools_called=[],
            input_tokens=llm_service.estimate_tokens(cleaned_message),
            output_tokens=0,
            cost_usd=0.0,
            latency_ms=1.5,
            status="refused",
            workspace_id=payload.workspace_id or 1,
            session=db,
        )
        raise InvalidPromptException(reason)

    response = await rag_service.answer_query(
        query=cleaned_message,
        session=db,
        workspace_id=payload.workspace_id,
        current_user=current_user,
    )

    return response
