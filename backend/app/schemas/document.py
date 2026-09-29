"""Document and chunk Pydantic v2 schemas."""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class DocumentChunkResponse(BaseModel):
    """Information for a single parsed chunk."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    chunk_id: str
    chunk_index: int
    page_number: int
    title: str
    content: str


class DocumentResponse(BaseModel):
    """Summary information for an uploaded document."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    workspace_id: int
    filename: str
    file_type: str
    file_size: int
    status: str
    chunk_count: int
    created_at: datetime
    updated_at: Optional[datetime] = None


class DocumentDetailResponse(DocumentResponse):
    """Detailed document information including all chunks."""

    chunks: List[DocumentChunkResponse] = Field(default_factory=list)


class DocumentPublishResponse(BaseModel):
    """Response after publishing a verified document."""

    id: int
    status: str
    message: str
