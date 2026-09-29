"""Verification Pydantic v2 schemas for Active Knowledge Verification Engine."""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class VerificationItemResponse(BaseModel):
    """Result of an individual synthetic RAG test question."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    question: str
    ground_truth: str
    rag_answer: str
    score: float
    status: str
    reason: Optional[str] = None


class VerificationReportResponse(BaseModel):
    """Complete evaluation report for a document."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    document_id: int
    workspace_id: int
    faithfulness_score: float
    status: str
    created_at: datetime
    items: List[VerificationItemResponse] = Field(default_factory=list)
