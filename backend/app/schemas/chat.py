"""Chat and RAG Request/Response schemas."""

from typing import List, Optional
from pydantic import BaseModel, Field


class CitationBadge(BaseModel):
    """Structured citation reference embedded in the RAG response."""

    doc_id: str = Field(..., description="Unique identifier of the source document", examples=["doc-04"])
    title: str = Field(..., description="Human-readable title of the cited article", examples=["Account Recovery & 2FA Reset Guide"])
    source_url: str = Field(..., description="Link or anchor to the referenced knowledge section", examples=["/docs/auth/account-recovery"])
    page: Optional[int] = Field(default=None, description="Page number if applicable", examples=[2])
    snippet: Optional[str] = Field(default=None, description="Referenced text snippet", examples=["Bảo hành 12 tháng..."])


class ChatRequest(BaseModel):
    """Customer chat input payload."""

    message: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="The customer's question or problem statement",
        examples=["How do I reset my password if I lost access to my email?"]
    )
    session_id: Optional[str] = Field(
        default=None,
        description="Optional session or conversation identifier for multi-turn tracking",
        examples=["sess-9a8b7c"]
    )
    workspace_id: Optional[int] = Field(
        default=None,
        description="Target workspace ID, defaults to Default Workspace",
        examples=[1]
    )


class ChatResponse(BaseModel):
    """Standardized response for customer-facing AI assistant."""

    response: str = Field(..., description="Grounded AI or fallback answer generated for the user")
    citations: List[CitationBadge] = Field(
        default_factory=list,
        description="List of verified knowledge base citations backing the response"
    )
    latency_ms: float = Field(..., description="Total processing latency in milliseconds")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score between 0.0 and 1.0")
    is_fallback: bool = Field(
        default=False,
        description="Indicates whether the response was generated via deterministic fallback mechanism"
    )
    fallback_reason: Optional[str] = Field(
        default=None,
        description="Reason if fallback was triggered, e.g. FREE_TIER_RATE_LIMIT_COOLDOWN"
    )
    escalation_recommended: Optional[bool] = Field(
        default=False,
        description="True if confidence was low or circuit breaker tripped, recommending ticket creation"
    )
