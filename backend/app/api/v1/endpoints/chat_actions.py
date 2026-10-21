"""Agent Tool User Confirmation Card Endpoints (REQ-14, Capability B)."""

import logging
from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.services.agent_tools import agent_tool_registry

logger = logging.getLogger("smartdesk.api.chat_actions")

router = APIRouter()


class ActionConfirmationRequest(BaseModel):
    """Payload to confirm or cancel a pending mutating tool action."""

    action_id: str
    confirmed: bool


class ActionConfirmationResponse(BaseModel):
    """Result of tool execution following user confirmation (compatible with CONTRACTS.md §8.4 and frontend types)."""

    action_id: str
    status: str = "executed"
    executed: bool = True
    result_message: str
    message: str
    ticket_id: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    result_data: Optional[Dict[str, Any]] = None


@router.post(
    "/confirm-action",
    response_model=ActionConfirmationResponse,
    status_code=status.HTTP_200_OK,
    summary="Confirm or Reject Pending Agent Tool Action",
    description="Executes a two-phase mutating tool (such as creating an escalation ticket or updating ticket priority) once confirmed by the user."
)
async def confirm_action(
    payload: ActionConfirmationRequest,
    db: AsyncSession = Depends(get_db)
) -> ActionConfirmationResponse:
    """Handles confirmation or rejection of pending agent tool actions."""
    outcome = await agent_tool_registry.execute_pending_action(
        action_id=payload.action_id,
        confirmed=payload.confirmed,
        db=db,
    )
    return ActionConfirmationResponse(
        action_id=outcome["action_id"],
        status=outcome["status"],
        executed=outcome["executed"],
        result_message=outcome["result_message"],
        message=outcome["message"],
        ticket_id=outcome.get("ticket_id"),
        data=outcome.get("data"),
        result_data=outcome.get("data"),
    )
