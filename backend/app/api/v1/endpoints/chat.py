"""Chat endpoint handling customer RAG inquiries with automatic fallback."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from app.schemas.chat import ChatRequest, ChatResponse
from app.services.rag_service import rag_service
from app.core.security import sanitize_input, check_prompt_injection
from app.core.exceptions import InvalidPromptException
from app.db.session import get_db

logger = logging.getLogger("smartdesk.api.chat")

router = APIRouter()


@router.post(
    "",
    response_model=ChatResponse,
    status_code=status.HTTP_200_OK,
    summary="Customer AI Assistant RAG Query",
    description=(
        "Processes customer inquiries using Google Gemini 1.5 Flash grounded on verified knowledge documents. "
        "Returns structured citations and latency. Automatically trips circuit breaker to FallbackService on failure."
    )
)
async def chat_with_assistant(
    payload: ChatRequest,
    db: AsyncSession = Depends(get_db)
) -> ChatResponse:
    """Customer chat endpoint supporting RAG grounding and graceful fallback."""
    # 1. Sanitize user input
    cleaned_message = sanitize_input(payload.message)
    if not cleaned_message:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Message content cannot be empty after sanitization."
        )

    # 2. Check for malicious prompt injection patterns
    is_suspicious, reason = check_prompt_injection(cleaned_message)
    if is_suspicious:
        logger.warning(f"Rejected malicious prompt: {reason}")
        raise InvalidPromptException(reason)

    # 3. Route to RAG Service
    response = await rag_service.answer_query(
        query=cleaned_message,
        session=db
    )

    return response
