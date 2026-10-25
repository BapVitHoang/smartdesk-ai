"""SSE Token-by-Token Streaming Endpoints for Customer RAG (REQ-04, REQ-10)."""

import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.endpoints.chat_actions import get_optional_current_user
from app.core.exceptions import InvalidPromptException
from app.core.prompts import prompt_registry
from app.core.security import check_prompt_injection, sanitize_input
from app.db.session import get_db
from app.models.user import User
from app.schemas.chat import ChatRequest
from app.services.ai_usage_logger import log_ai_call
from app.services.llm_service import llm_service
from app.services.rag_service import rag_service

logger = logging.getLogger("smartdesk.api.chat_stream")

router = APIRouter()


@router.post(
    "/stream",
    status_code=status.HTTP_200_OK,
    summary="Stream Customer Support Query (SSE)",
    description="Streams the AI support response token-by-token using Server-Sent Events (SSE) with metadata, token, and done events."
)
async def chat_stream(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
) -> StreamingResponse:
    """Streams RAG chat answer token by token with guardrail validation."""
    cleaned_message = sanitize_input(request.message)
    if not cleaned_message:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Message content cannot be empty after sanitization."
        )

    is_suspicious, reason = check_prompt_injection(cleaned_message)
    if is_suspicious:
        logger.warning(f"Rejected malicious prompt on /chat/stream: {reason}")
        await log_ai_call(
            endpoint="/api/v1/chat/stream",
            prompt_version=prompt_registry.get_prompt_version("rag_customer_support"),
            provider="guardrail",
            model_name=llm_service.active_model_name,
            tools_called=[],
            input_tokens=llm_service.estimate_tokens(cleaned_message),
            output_tokens=0,
            cost_usd=0.0,
            latency_ms=1.2,
            status="refused",
            workspace_id=request.workspace_id or 1,
            session=db,
        )
        raise InvalidPromptException(reason)

    return StreamingResponse(
        rag_service.answer_query_stream(
            query=cleaned_message,
            session=db,
            workspace_id=request.workspace_id,
            session_id=request.session_id,
            current_user=current_user,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
