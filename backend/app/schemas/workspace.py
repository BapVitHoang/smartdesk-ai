"""Workspace Pydantic v2 schemas for multi-tenant configuration."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class WorkspaceBase(BaseModel):
    """Base workspace attributes."""

    slug: str = Field(..., min_length=2, max_length=64, description="Unique slug for the workspace")
    name: str = Field(..., min_length=2, max_length=128, description="Display name of the organization")
    industry: str = Field(..., min_length=2, max_length=128, description="Industry or domain domain")
    persona_name: str = Field(..., min_length=2, max_length=128, description="AI Bot persona name")
    tone_of_voice: str = Field(..., min_length=2, max_length=255, description="Tone of voice guideline")
    business_rules: str = Field(default="", description="Strict operational rules and policies")


class WorkspaceCreate(WorkspaceBase):
    """Payload to create a new workspace."""
    pass


class WorkspaceUpdate(BaseModel):
    """Payload to update an existing workspace."""

    name: Optional[str] = None
    industry: Optional[str] = None
    persona_name: Optional[str] = None
    tone_of_voice: Optional[str] = None
    business_rules: Optional[str] = None


class WorkspaceResponse(WorkspaceBase):
    """Serialized workspace output."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
