"""Agent Copilot endpoints: AI-assisted draft reply regeneration and triage support."""

from fastapi import APIRouter, Depends, Path, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import logging

from app.schemas.ticket import TicketResponse
from app.models.ticket import Ticket
from app.services.ticket_service import ticket_service
from app.core.exceptions import TicketNotFoundException
from app.db.session import get_db

logger = logging.getLogger("smartdesk.api.agent")

router = APIRouter()


@router.post(
    "/tickets/{ticket_id}/generate-draft",
    response_model=TicketResponse,
    status_code=status.HTTP_200_OK,
    summary="Regenerate AI Draft Reply (Copilot)",
    description="Invokes AI Copilot to generate a fresh, personalized resolution draft for the support agent to inspect and edit."
)
async def generate_draft_reply(
    ticket_id: str = Path(..., description="Ticket integer ID or formatted code"),
    db: AsyncSession = Depends(get_db)
) -> TicketResponse:
    """Regenerates AI draft reply for a given ticket."""
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
        description=ticket.description
    )

    ticket.ai_draft_reply = new_draft
    await db.commit()
    await db.refresh(ticket)

    return TicketResponse.model_validate(ticket)
