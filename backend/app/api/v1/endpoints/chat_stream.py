"""SSE Token-by-Token Streaming Endpoints for Customer RAG (REQ-04, REQ-10)."""

import json
import logging
from typing import AsyncGenerator
from fastapi import APIRouter, Depends, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.chat import ChatRequest

logger = logging.getLogger("smartdesk.api.chat_stream")

router = APIRouter()


async def dummy_sse_stream(message: str) -> AsyncGenerator[str, None]:
    """Yields SSE events: metadata, tokens, and done."""
    meta = {
        "type": "metadata",
        "citations": [],
        "confidence": 0.90,
        "is_fallback": False,
        "escalation_recommended": False,
        "tools_called": [],
        "pending_action": None,
    }
    yield f"data: {json.dumps(meta, ensure_ascii=False)}\n\n"

    words = message.split()
    for w in words:
        token_payload = {"type": "token", "delta": f" {w}"}
        yield f"data: {json.dumps(token_payload, ensure_ascii=False)}\n\n"

    done_payload = {"type": "done", "latency_ms": 120.0, "prompt_version": "rag_customer_support@v1.0.0"}
    yield f"data: {json.dumps(done_payload, ensure_ascii=False)}\n\n"


@router.post(
    "/stream",
    status_code=status.HTTP_200_OK,
    summary="Stream Customer Support Query (SSE)",
    description="Streams the AI support response token-by-token using Server-Sent Events (SSE)."
)
async def chat_stream(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db)
) -> StreamingResponse:
    """Streams RAG chat answer token by token."""
    return StreamingResponse(
        dummy_sse_stream(request.message),
        media_type="text/event-stream"
    )
