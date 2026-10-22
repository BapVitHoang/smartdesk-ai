"""Agent Tool User Confirmation Card Endpoints (REQ-14, Capability B)."""

import logging
from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.services.agent_tools import agent_tool_registry

logger = logging.getLogger("smartdesk.api.chat_actions")

security_bearer = HTTPBearer(auto_error=False)


async def get_optional_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    """Gracefully resolves authenticated user if Bearer token present, else None."""
    if not credentials or not credentials.credentials:
        return None
    try:
        return await get_current_user(credentials=credentials, db=db)
    except HTTPException:
        return None


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
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
) -> ActionConfirmationResponse:
    """Handles confirmation or rejection of pending agent tool actions."""
    outcome = await agent_tool_registry.execute_pending_action(
        action_id=payload.action_id,
        confirmed=payload.confirmed,
        db=db,
        current_user=current_user,
    )
    if not outcome.get("executed") and outcome.get("error_code"):
        err_code = outcome["error_code"]
        msg = outcome.get("message", "Thao tác không hợp lệ.")
        if err_code == "ACTION_NOT_FOUND":
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=msg)
        elif err_code == "ACTION_FORBIDDEN":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=msg)
        elif err_code in ("ALREADY_EXECUTED", "ACTION_EXPIRED"):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)

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
