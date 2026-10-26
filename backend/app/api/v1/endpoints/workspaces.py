"""Workspace management API endpoints for multi-domain tenant support."""

from typing import List
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.models.workspace import Workspace
from app.models.user import User
from app.core.security import check_prompt_injection
from app.core.deps import require_role
from app.schemas.workspace import (
    WorkspaceCreate,
    WorkspaceUpdate,
    WorkspaceResponse,
)

logger = logging.getLogger("smartdesk.api.workspaces")
router = APIRouter()


@router.get("", response_model=List[WorkspaceResponse], summary="List all workspaces")
async def list_workspaces(
    db: AsyncSession = Depends(get_db),
) -> List[WorkspaceResponse]:
    """Retrieve all available workspace profiles."""
    result = await db.execute(select(Workspace).order_by(Workspace.id))
    workspaces = result.scalars().all()
    return [WorkspaceResponse.model_validate(w) for w in workspaces]


@router.post(
    "",
    response_model=WorkspaceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create workspace",
)
async def create_workspace(
    payload: WorkspaceCreate,
    _admin: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
) -> WorkspaceResponse:
    """Create a new domain workspace."""
    # Prompt injection guardrail on persona and rules
    for val, field_name in [
        (payload.persona_name, "persona_name"),
        (payload.tone_of_voice, "tone_of_voice"),
        (payload.business_rules, "business_rules"),
    ]:
        if val:
            is_suspicious, reason = check_prompt_injection(val)
            if is_suspicious:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"PROMPT_SECURITY_VIOLATION: Trường {field_name} chứa ký tự hoặc mẫu độc hại ({reason}).",
                )

    # Check if slug already exists
    existing = await db.execute(select(Workspace).where(Workspace.slug == payload.slug))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Slug '{payload.slug}' đã tồn tại trong hệ thống.",
        )

    ws = Workspace(
        slug=payload.slug,
        name=payload.name,
        industry=payload.industry,
        persona_name=payload.persona_name,
        tone_of_voice=payload.tone_of_voice,
        business_rules=payload.business_rules,
    )
    db.add(ws)
    await db.commit()
    await db.refresh(ws)
    logger.info(f"Created new workspace ID={ws.id} slug={ws.slug}")
    return WorkspaceResponse.model_validate(ws)


@router.get("/{id}", response_model=WorkspaceResponse, summary="Get workspace details")
async def get_workspace(
    id: int, db: AsyncSession = Depends(get_db)
) -> WorkspaceResponse:
    """Get workspace details by ID."""
    result = await db.execute(select(Workspace).where(Workspace.id == id))
    ws = result.scalar_one_or_none()
    if not ws:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy Workspace với ID {id}.",
        )
    return WorkspaceResponse.model_validate(ws)


@router.put("/{id}", response_model=WorkspaceResponse, summary="Update workspace")
async def update_workspace(
    id: int,
    payload: WorkspaceUpdate,
    _admin: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
) -> WorkspaceResponse:
    """Update persona, tone of voice, or business rules of a workspace."""
    result = await db.execute(select(Workspace).where(Workspace.id == id))
    ws = result.scalar_one_or_none()
    if not ws:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy Workspace với ID {id}.",
        )

    update_data = payload.model_dump(exclude_unset=True)
    for field, val in update_data.items():
        if val is not None:
            if isinstance(val, str) and field in {
                "persona_name",
                "tone_of_voice",
                "business_rules",
            }:
                is_suspicious, reason = check_prompt_injection(val)
                if is_suspicious:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"PROMPT_SECURITY_VIOLATION: Trường {field} chứa ký tự hoặc mẫu độc hại ({reason}).",
                    )
            setattr(ws, field, val)

    await db.commit()
    await db.refresh(ws)
    logger.info(f"Updated workspace ID={ws.id}")
    return WorkspaceResponse.model_validate(ws)


@router.delete(
    "/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete workspace",
    description="Deletes a workspace by ID (restricted to admin). Default workspace ID 1 cannot be deleted.",
)
async def delete_workspace(
    id: int,
    admin_user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Deletes a workspace by ID. Blocks deletion of default workspace (ID=1)."""
    if id == 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Không thể xóa Workspace mặc định (ID 1).",
        )

    result = await db.execute(select(Workspace).where(Workspace.id == id))
    ws = result.scalar_one_or_none()
    if not ws:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy Workspace với ID {id}.",
        )

    await db.delete(ws)
    await db.commit()
    logger.info(f"Deleted workspace ID={id} slug={ws.slug}")
    return None
