"""Ticket management endpoints (CRUD, triage filtering, and agent customization)."""

from typing import List, Optional
from fastapi import APIRouter, Depends, Query, Path, Response, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, desc, asc, func
import logging

from app.schemas.ticket import TicketCreate, TicketUpdate, TicketResponse
from app.models.ticket import Ticket
from app.models.user import User
from app.services.ticket_service import ticket_service
from app.core.exceptions import TicketNotFoundException
from app.core.security import sanitize_input, check_prompt_injection
from app.core.deps import get_current_user, require_role
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
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> TicketResponse:
    """Create a new ticket with automatic Copilot triage. Requires authentication (REQ-SEC-03)."""
    # Enforce customer ownership: regular users can only submit tickets for their own email/name
    if current_user.role != "admin":
        ticket_in.customer_email = current_user.email
        ticket_in.customer_name = current_user.full_name or current_user.email.split("@")[0]
    else:
        # Support staff / admin can specify customer details or fall back to authenticated staff
        if not ticket_in.customer_email:
            ticket_in.customer_email = current_user.email
        if not ticket_in.customer_name:
            ticket_in.customer_name = current_user.full_name or "Support Staff"

    # Sanitize text fields
    ticket_in.customer_name = sanitize_input(ticket_in.customer_name)
    ticket_in.subject = sanitize_input(ticket_in.subject)
    ticket_in.description = sanitize_input(ticket_in.description)

    # Prompt injection guardrail
    for text_val, field_name in [(ticket_in.subject, "subject"), (ticket_in.description, "description")]:
        is_suspicious, reason = check_prompt_injection(text_val)
        if is_suspicious:
            logger.warning(f"Prompt injection rejected in ticket {field_name}: {reason}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"PROMPT_SECURITY_VIOLATION: Nội dung trường {field_name} không hợp lệ hoặc chứa mã độc prompt injection ({reason})."
            )
    ticket_in.description = sanitize_input(ticket_in.description)

    created_ticket = await ticket_service.create_ticket(db, ticket_in)
    return TicketResponse.model_validate(created_ticket)


@router.get(
    "",
    response_model=List[TicketResponse],
    status_code=status.HTTP_200_OK,
    summary="List and Filter Support Tickets",
    description="Query tickets with optional filtering, server-side sorting, pagination, and total count header. Enforces RBAC tenant data isolation."
)
async def list_tickets(
    response: Response,
    workspace_id: Optional[int] = Query(None, description="Filter by workspace ID"),
    status: Optional[str] = Query(None, description="Filter by status (e.g. open, in_progress, resolved)"),
    category: Optional[str] = Query(None, description="Filter by category"),
    priority: Optional[str] = Query(None, description="Filter by priority (Low, Medium, High, Urgent)"),
    search: Optional[str] = Query(None, description="Search term in subject, description, customer name, or ticket code"),
    sort_by: str = Query("created_at", description="Sort field: created_at | priority | status | sla_hours"),
    sort_order: str = Query("desc", description="Sort direction: asc | desc"),
    skip: int = Query(0, ge=0, description="Offset for pagination"),
    limit: int = Query(20, ge=1, le=100, description="Limit results"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> List[TicketResponse]:
    """Retrieve filtered and sorted ticket list with X-Total-Count header."""
    query = select(Ticket)
    count_query = select(func.count(Ticket.id))

    # RBAC Data Isolation: Regular users only see tickets created under their email
    if current_user.role != "admin":
        query = query.where(Ticket.customer_email == current_user.email)
        count_query = count_query.where(Ticket.customer_email == current_user.email)

    if workspace_id:
        query = query.where(Ticket.workspace_id == workspace_id)
        count_query = count_query.where(Ticket.workspace_id == workspace_id)
    if status:
        query = query.where(Ticket.status == status.lower())
        count_query = count_query.where(Ticket.status == status.lower())
    if category:
        query = query.where(Ticket.category == category)
        count_query = count_query.where(Ticket.category == category)
    if priority:
        query = query.where(Ticket.priority == priority)
        count_query = count_query.where(Ticket.priority == priority)
    if search:
        search_pattern = f"%{search}%"
        search_filter = or_(
            Ticket.ticket_code.ilike(search_pattern),
            Ticket.subject.ilike(search_pattern),
            Ticket.description.ilike(search_pattern),
            Ticket.customer_name.ilike(search_pattern),
            Ticket.customer_email.ilike(search_pattern)
        )
        query = query.where(search_filter)
        count_query = count_query.where(search_filter)

    # 1. Total matching count for pagination header (REQ-30)
    total_count = (await db.execute(count_query)).scalar() or 0
    response.headers["X-Total-Count"] = str(total_count)

    # 2. Server-side sorting
    sort_col = Ticket.created_at
    if sort_by == "priority":
        sort_col = Ticket.priority
    elif sort_by == "status":
        sort_col = Ticket.status
    elif sort_by in {"sla_hours", "sla_due_date"}:
        sort_col = Ticket.estimated_response_hours
    elif sort_by == "created_at":
        sort_col = Ticket.created_at

    order_fn = asc if sort_order.lower() == "asc" else desc
    query = query.order_by(order_fn(sort_col)).offset(skip).limit(limit)

    result = await db.execute(query)
    tickets = result.scalars().all()

    return [TicketResponse.model_validate(t) for t in tickets]


@router.get(
    "/{ticket_id}",
    response_model=TicketResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Ticket Details",
    description="Fetch a ticket by integer ID or formatted code (#TICK-XXXX). Enforces RBAC ownership."
)
async def get_ticket(
    ticket_id: str = Path(..., description="Ticket integer ID or formatted code"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> TicketResponse:
    """Retrieve ticket details with customer ownership validation."""
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

    # RBAC Data Isolation: Regular users cannot inspect other customers' tickets
    if current_user.role != "admin" and ticket.customer_email != current_user.email:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Quyền truy cập bị từ chối. Bạn chỉ có thể xem phiếu hỗ trợ của chính mình."
        )

    return TicketResponse.model_validate(ticket)


@router.patch(
    "/{ticket_id}",
    response_model=TicketResponse,
    status_code=status.HTTP_200_OK,
    summary="Update Ticket or Edit AI Draft",
    description="Update status (in_progress, resolved) or customize the pre-drafted response (restricted to admin)."
)
async def update_ticket(
    ticket_id: str = Path(..., description="Ticket integer ID or formatted code"),
    ticket_update: TicketUpdate = ...,
    admin_user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db)
) -> TicketResponse:
    """Update ticket properties and draft reply (restricted to admin/agent role)."""
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


@router.delete(
    "/{ticket_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Support Ticket",
    description="Deletes a support ticket by integer ID or formatted code (restricted to admin role)."
)
async def delete_ticket(
    ticket_id: str = Path(..., description="Ticket integer ID or formatted code"),
    admin_user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db)
) -> None:
    """Deletes a ticket from database (admin only)."""
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

    await db.delete(ticket)
    await db.commit()
    return None
