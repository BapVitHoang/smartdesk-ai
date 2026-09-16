"""Ticket management endpoints (CRUD, triage filtering, and agent customization)."""

from typing import List, Optional
from fastapi import APIRouter, Depends, Query, Path, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, desc
import logging

from app.schemas.ticket import TicketCreate, TicketUpdate, TicketResponse
from app.models.ticket import Ticket
from app.services.ticket_service import ticket_service
from app.core.exceptions import TicketNotFoundException
from app.core.security import sanitize_input
from app.db.session import get_db

logger = logging.getLogger("smartdesk.api.tickets")

router = APIRouter()


@router.post(
    "",
    response_model=TicketResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create or Escalate Support Ticket",
    description="Submits a customer support ticket, automatically generating #TICK-XXXX code, AI triage tags, and an AI draft reply."
)
async def create_ticket(
    ticket_in: TicketCreate,
    db: AsyncSession = Depends(get_db)
) -> TicketResponse:
    """Create a new ticket with automatic Copilot triage."""
    # Sanitize text fields
    ticket_in.customer_name = sanitize_input(ticket_in.customer_name)
    ticket_in.subject = sanitize_input(ticket_in.subject)
    ticket_in.description = sanitize_input(ticket_in.description)

    created_ticket = await ticket_service.create_ticket(db, ticket_in)
    return TicketResponse.model_validate(created_ticket)


@router.get(
    "",
    response_model=List[TicketResponse],
    status_code=status.HTTP_200_OK,
    summary="List and Filter Support Tickets",
    description="Query tickets with optional filtering by status, category, priority, and text search for Agent Dashboard."
)
async def list_tickets(
    status: Optional[str] = Query(None, description="Filter by status (e.g. open, in_progress, resolved)"),
    category: Optional[str] = Query(None, description="Filter by category"),
    priority: Optional[str] = Query(None, description="Filter by priority (Low, Medium, High, Urgent)"),
    search: Optional[str] = Query(None, description="Search term in subject, description, customer name, or ticket code"),
    skip: int = Query(0, ge=0, description="Offset for pagination"),
    limit: int = Query(20, ge=1, le=100, description="Limit results"),
    db: AsyncSession = Depends(get_db)
) -> List[TicketResponse]:
    """Retrieve filtered ticket list sorted by newest first."""
    query = select(Ticket)

    if status:
        query = query.where(Ticket.status == status.lower())
    if category:
        query = query.where(Ticket.category == category)
    if priority:
        query = query.where(Ticket.priority == priority)
    if search:
        search_pattern = f"%{search}%"
        query = query.where(
            or_(
                Ticket.ticket_code.ilike(search_pattern),
                Ticket.subject.ilike(search_pattern),
                Ticket.description.ilike(search_pattern),
                Ticket.customer_name.ilike(search_pattern),
                Ticket.customer_email.ilike(search_pattern)
            )
        )

    query = query.order_by(desc(Ticket.created_at)).offset(skip).limit(limit)
    result = await db.execute(query)
    tickets = result.scalars().all()

    return [TicketResponse.model_validate(t) for t in tickets]


@router.get(
    "/{ticket_id}",
    response_model=TicketResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Ticket Details",
    description="Fetch a ticket by integer ID or formatted code (#TICK-XXXX)."
)
async def get_ticket(
    ticket_id: str = Path(..., description="Ticket integer ID or formatted code"),
    db: AsyncSession = Depends(get_db)
) -> TicketResponse:
    """Retrieve ticket details."""
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

    return TicketResponse.model_validate(ticket)


@router.patch(
    "/{ticket_id}",
    response_model=TicketResponse,
    status_code=status.HTTP_200_OK,
    summary="Update Ticket or Edit AI Draft",
    description="Update status (in_progress, resolved) or customize the pre-drafted response."
)
async def update_ticket(
    ticket_id: str = Path(..., description="Ticket integer ID or formatted code"),
    ticket_update: TicketUpdate = ...,
    db: AsyncSession = Depends(get_db)
) -> TicketResponse:
    """Update ticket properties and draft reply."""
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

    if ticket_update.status is not None:
        ticket.status = ticket_update.status.value
    if ticket_update.ai_draft_reply is not None:
        ticket.ai_draft_reply = ticket_update.ai_draft_reply
    if ticket_update.category is not None:
        ticket.category = ticket_update.category
    if ticket_update.priority is not None:
        ticket.priority = ticket_update.priority.value
        ticket.estimated_response_hours = ticket_service.calculate_sla_hours(ticket.priority)

    await db.commit()
    await db.refresh(ticket)

    return TicketResponse.model_validate(ticket)
