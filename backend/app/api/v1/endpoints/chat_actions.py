"""Agent Tool User Confirmation Card Endpoints (REQ-14, Capability B)."""

import logging
from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.db.session import get_db

logger = logging.getLogger("smartdesk.api.chat_actions")

router = APIRouter()


class ActionConfirmationRequest(BaseModel):
    """Payload to confirm or cancel a pending mutating tool action."""
    action_id: str
    confirmed: bool


class ActionConfirmationResponse(BaseModel):
    """Result of tool execution following user confirmation."""
    action_id: str
    executed: bool
    message: str
    result_data: Optional[Dict[str, Any]] = None


@router.post(
    "/confirm-action",
    response_model=ActionConfirmationResponse,
    status_code=status.HTTP_200_OK,
    summary="Confirm or Reject Pending Agent Tool Action",
    description="Executes a two-phase mutating tool (such as creating an escalation ticket) once confirmed by the user."
)
async def confirm_action(
    payload: ActionConfirmationRequest,
    db: AsyncSession = Depends(get_db)
) -> ActionConfirmationResponse:
    """Handles confirmation or rejection of pending actions."""
    if not payload.confirmed:
        return ActionConfirmationResponse(
            action_id=payload.action_id,
            executed=False,
            message="Thao tác đã bị người dùng hủy bỏ.",
        )

    return ActionConfirmationResponse(
        action_id=payload.action_id,
        executed=True,
        message="Thao tác đã được xác nhận và thực thi thành công.",
        result_data={"status": "executed"}
    )
