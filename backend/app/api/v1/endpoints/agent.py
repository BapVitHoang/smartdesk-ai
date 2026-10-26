"""Agent Copilot endpoints: AI-assisted draft reply regeneration and triage support."""

from fastapi import APIRouter, Depends, Path, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
import logging
from typing import Any

from app.schemas.ticket import TicketResponse
from app.models.ticket import Ticket
from app.models.user import User
from app.services.ticket_service import ticket_service
from app.services.llm_service import llm_service
from app.core.exceptions import TicketNotFoundException
from app.core.deps import require_role
from app.db.session import get_db

logger = logging.getLogger("smartdesk.api.agent")

router = APIRouter()


class ResetCooldownResponse(BaseModel):
    """Response schema for resetting the 60s Cost-Guard Circuit Breaker."""

    status: str = "success"
    message: str
    cooldown_active: bool = False


@router.post(
    "/reset-cooldown",
    response_model=ResetCooldownResponse,
    status_code=status.HTTP_200_OK,
    summary="Reset Cost-Guard Circuit Breaker Cooldown",
    description="Manually clears the 60s Free-Tier HTTP 429 cooldown lock so Cloud Gemini calls resume immediately."
)
async def reset_circuit_breaker_cooldown(
    _admin: User = Depends(require_role("admin"))
) -> ResetCooldownResponse:
    """Resets the Cost-Guard cooldown timer on LLMService and EmbeddingService."""
    llm_service.reset_cooldown()
    return ResetCooldownResponse(
        status="success",
        message="Circuit breaker cooldown has been reset. Cloud Gemini calls re-enabled.",
        cooldown_active=llm_service.is_in_cooldown(),
    )


@router.post(
    "/tickets/{ticket_id}/generate-draft",
    response_model=TicketResponse,
    status_code=status.HTTP_200_OK,
    summary="Regenerate AI Draft Reply (Copilot)",
    description="Invokes AI Copilot to generate a fresh, personalized resolution draft for the support agent to inspect and edit."
)
async def generate_draft_reply(
    ticket_id: str = Path(..., description="Ticket integer ID or formatted code"),
    admin_user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db)
) -> TicketResponse:
    """Regenerates AI draft reply for a given ticket (restricted to admin/agent role)."""
    query = select(Ticket)
    if ticket_id.isdigit():
        query = query.where(Ticket.id == int(ticket_id))
    else:
        formatted_code = ticket_id if ticket_id.startswith("#") else f"#{ticket_id}"
        query = query.where(or_(Ticket.ticket_code == ticket_id, Ticket.ticket_code == formatted_code))

    result = await db.execute(query)
    ticket = result.scalars().first()

    if not ticket:
        raise TicketNotFoundException(ticket_id)

    new_draft = await ticket_service.generate_draft_reply(
        customer_name=ticket.customer_name,
        category=ticket.category,
        priority=ticket.priority,
        subject=ticket.subject,
        description=ticket.description,
        workspace_id=ticket.workspace_id,
        db=db
    )

    ticket.ai_draft_reply = new_draft
    await db.commit()
    await db.refresh(ticket)

    return TicketResponse.model_validate(ticket)
