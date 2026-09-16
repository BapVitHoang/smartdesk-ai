"""Health and latency benchmark response schemas."""

from typing import Optional
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """System health and operational readiness response."""

    status: str = Field(..., description="Overall service status (e.g. 'ok')", examples=["ok"])
    database: str = Field(..., description="Database connection health", examples=["connected"])
    version: str = Field(..., description="API Version", examples=["1.0.0"])


class SmokeTestResponse(BaseModel):
    """Smoke test benchmarking response executing live LLM round-trip."""

    model: str = Field(..., description="The LLM model tested", examples=["gemini-1.5-flash"])
    latency_ms: float = Field(..., description="Total round-trip latency in milliseconds", examples=[852.53])
    status: str = Field(..., description="Test outcome: 'PASS' or 'FAIL'", examples=["PASS"])
    sample_prompt: str = Field(..., description="The prompt dispatched to the model")
    sample_response: str = Field(..., description="Actual response text returned by the model")
    note: Optional[str] = Field(default=None, description="Additional context, e.g., circuit breaker status")
