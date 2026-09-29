"""Workspace management API endpoints for multi-domain tenant support."""

from typing import List
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.models.workspace import Workspace
from app.schemas.workspace import (
    WorkspaceCreate,
    WorkspaceUpdate,
    WorkspaceResponse,
)

logger = logging.getLogger("smartdesk.api.workspaces")
router = APIRouter()


@router.get("", response_model=List[WorkspaceResponse], summary="List all workspaces")
async def list_workspaces(db: AsyncSession = Depends(get_db)) -> List[WorkspaceResponse]:
    """Retrieve all available workspace profiles."""
    result = await db.execute(select(Workspace).order_by(Workspace.id))
    workspaces = result.scalars().all()
    return [WorkspaceResponse.model_validate(w) for w in workspaces]


@router.post("", response_model=WorkspaceResponse, status_code=status.HTTP_201_CREATED, summary="Create workspace")
async def create_workspace(
    payload: WorkspaceCreate,
    db: AsyncSession = Depends(get_db)
) -> WorkspaceResponse:
    """Create a new domain workspace."""
    # Check if slug already exists
    existing = await db.execute(select(Workspace).where(Workspace.slug == payload.slug))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Slug '{payload.slug}' đã tồn tại trong hệ thống."
        )

    ws = Workspace(
        slug=payload.slug,
        name=payload.name,
        industry=payload.industry,
        persona_name=payload.persona_name,
        tone_of_voice=payload.tone_of_voice,
        business_rules=payload.business_rules
    )
    db.add(ws)
    await db.commit()
    await db.refresh(ws)
    logger.info(f"Created new workspace ID={ws.id} slug={ws.slug}")
    return WorkspaceResponse.model_validate(ws)


@router.get("/{id}", response_model=WorkspaceResponse, summary="Get workspace details")
async def get_workspace(
    id: int,
    db: AsyncSession = Depends(get_db)
) -> WorkspaceResponse:
    """Get workspace details by ID."""
    result = await db.execute(select(Workspace).where(Workspace.id == id))
    ws = result.scalar_one_or_none()
    if not ws:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy Workspace với ID {id}."
        )
    return WorkspaceResponse.model_validate(ws)


@router.put("/{id}", response_model=WorkspaceResponse, summary="Update workspace")
async def update_workspace(
    id: int,
    payload: WorkspaceUpdate,
    db: AsyncSession = Depends(get_db)
) -> WorkspaceResponse:
    """Update persona, tone of voice, or business rules of a workspace."""
    result = await db.execute(select(Workspace).where(Workspace.id == id))
    ws = result.scalar_one_or_none()
    if not ws:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy Workspace với ID {id}."
        )

    update_data = payload.model_dump(exclude_unset=True)
    for field, val in update_data.items():
        if val is not None:
            setattr(ws, field, val)

    await db.commit()
    await db.refresh(ws)
    logger.info(f"Updated workspace ID={ws.id}")
    return WorkspaceResponse.model_validate(ws)
