"""Verification Pydantic v2 schemas for Active Knowledge Verification Engine (with Multi-Agent Trace)."""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.ai_structured import AgentHandOffStep


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
    """Complete evaluation report for a document including multi-agent hand-off trace (REQ-17)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    document_id: int
    workspace_id: int
    faithfulness_score: float
    status: str
    created_at: datetime
    items: List[VerificationItemResponse] = Field(default_factory=list)
    agent_trace: List[AgentHandOffStep] = Field(default_factory=list)

    @model_validator(mode="after")
    def populate_agent_trace_if_empty(self) -> "VerificationReportResponse":
        """Falls back to the trace recorded in this process when the report row has none persisted."""
        if not self.agent_trace:
            try:
                from app.services.verification_service import verification_service

                self.agent_trace = verification_service.get_agent_trace(
                    document_id=self.document_id,
                    faithfulness_score=self.faithfulness_score,
                    status=self.status,
                    item_count=len(self.items) or 3,
                )
            except Exception:
                pass
        return self
