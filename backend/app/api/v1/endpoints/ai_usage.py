"""AI Usage Observability, Cost-Guard Telemetry & Cooldown Reset Endpoints (REQ-22, REQ-33)."""

import logging
from typing import Any, Dict, List
from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import require_role
from app.db.session import get_db
from app.models.ai_usage import AIUsageLog
from app.services.llm_service import llm_service

logger = logging.getLogger("smartdesk.api.ai_usage")

router = APIRouter()


class AIUsageSummaryResponse(BaseModel):
    """Aggregated KPIs for AI cost, token, and latency observability (compatible with CONTRACTS.md §8.8 & frontend types)."""

    total_requests: int
    total_tokens: int
    total_input_tokens: int
    total_output_tokens: int
    total_cost_usd: float
    avg_cost_usd: float = 0.0
    avg_latency_ms: float
    success_count: int
    fallback_count: int
    refused_count: int
    error_count: int
    cooldown_active: bool = False
    model_breakdown: Dict[str, int] = {}
    recent_logs: List[Dict[str, Any]]


class ResetCooldownResponse(BaseModel):
    """Response schema for resetting the 60s Cost-Guard Circuit Breaker."""

    status: str = "success"
    message: str
    cooldown_active: bool = False


async def _build_usage_summary(limit: int, db: AsyncSession) -> AIUsageSummaryResponse:
    """Computes aggregated AI usage stats and formats recent logs."""
    result = await db.execute(
        select(AIUsageLog)
        .order_by(desc(AIUsageLog.created_at), desc(AIUsageLog.id))
        .limit(limit)
    )
    logs = result.scalars().all()

    total_res = await db.execute(select(func.count(AIUsageLog.id)))
    total_count = int(total_res.scalar() or 0)

    success_res = await db.execute(
        select(func.count(AIUsageLog.id)).where(AIUsageLog.status == "success")
    )
    success_count = int(success_res.scalar() or 0)

    fallback_res = await db.execute(
        select(func.count(AIUsageLog.id)).where(AIUsageLog.status == "fallback")
    )
    fallback_count = int(fallback_res.scalar() or 0)

    refused_res = await db.execute(
        select(func.count(AIUsageLog.id)).where(AIUsageLog.status == "refused")
    )
    refused_count = int(refused_res.scalar() or 0)

    cost_res = await db.execute(select(func.sum(AIUsageLog.cost_usd)))
    total_cost = round(float(cost_res.scalar() or 0.0), 6)

    latency_res = await db.execute(select(func.avg(AIUsageLog.latency_ms)))
    avg_latency = round(float(latency_res.scalar() or 0.0), 2)

    in_tokens_res = await db.execute(select(func.sum(AIUsageLog.input_tokens)))
    total_in = int(in_tokens_res.scalar() or 0)

    out_tokens_res = await db.execute(select(func.sum(AIUsageLog.output_tokens)))
    total_out = int(out_tokens_res.scalar() or 0)

    total_tok = total_in + total_out

    # Group by model_name for breakdown chart
    model_rows = await db.execute(
        select(AIUsageLog.model_name, func.count(AIUsageLog.id)).group_by(
            AIUsageLog.model_name
        )
    )
    model_breakdown: Dict[str, int] = {
        str(row[0] or "unknown"): int(row[1] or 0) for row in model_rows.all()
    }

    recent_logs = [
        {
            "id": log.id,
            "trace_id": f"tr-{1000 + (log.id or 0)}",
            "endpoint": log.endpoint,
            "prompt_version": log.prompt_version,
            "provider": log.provider,
            "model_name": log.model_name,
            "tools_called": log.tools_called or [],
            "input_tokens": log.input_tokens,
            "output_tokens": log.output_tokens,
            "prompt_tokens": log.input_tokens,
            "completion_tokens": log.output_tokens,
            "total_tokens": log.total_tokens,
            "cost_usd": log.cost_usd,
            "latency_ms": log.latency_ms,
            "status": log.status,
            "workspace_id": log.workspace_id,
            "created_at": log.created_at.isoformat() if log.created_at else None,
        }
        for log in logs
    ]

    return AIUsageSummaryResponse(
        total_requests=total_count,
        total_tokens=total_tok,
        total_input_tokens=total_in,
        total_output_tokens=total_out,
        total_cost_usd=total_cost,
        avg_cost_usd=round(total_cost / total_count, 6) if total_count else 0.0,
        avg_latency_ms=avg_latency,
        success_count=success_count,
        fallback_count=fallback_count,
        refused_count=refused_count,
        error_count=max(
            0, total_count - success_count - fallback_count - refused_count
        ),
        cooldown_active=llm_service.is_in_cooldown(),
        model_breakdown=model_breakdown,
        recent_logs=recent_logs,
    )


@router.get(
    "",
    response_model=AIUsageSummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Get AI Usage & Cost Observability Summary",
    description="Returns aggregated metrics on AI request count, token consumption, cost in USD, and recent telemetry logs.",
)
async def get_ai_usage_summary(
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _admin: Any = Depends(require_role("admin")),
) -> AIUsageSummaryResponse:
    """Retrieves AI observability summary and recent request logs."""
    return await _build_usage_summary(limit=limit, db=db)


@router.get(
    "/summary",
    response_model=AIUsageSummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Get AI Usage Summary Alias",
)
async def get_ai_usage_summary_alias(
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _admin: Any = Depends(require_role("admin")),
) -> AIUsageSummaryResponse:
    """Alias endpoint for frontend telemetry service."""
    return await _build_usage_summary(limit=limit, db=db)


@router.post(
    "/reset-cooldown",
    response_model=ResetCooldownResponse,
    status_code=status.HTTP_200_OK,
    summary="Reset Cost-Guard Circuit Breaker Cooldown",
    description="Manually clears the 60s Free-Tier HTTP 429 cooldown lock so Cloud Gemini calls resume immediately.",
)
async def reset_circuit_breaker_cooldown(
    _admin: Any = Depends(require_role("admin")),
) -> ResetCooldownResponse:
    """Resets the Cost-Guard cooldown timer on LLMService and EmbeddingService."""
    llm_service.reset_cooldown()
    return ResetCooldownResponse(
        status="success",
        message="Circuit breaker cooldown has been reset. Cloud Gemini calls re-enabled.",
        cooldown_active=llm_service.is_in_cooldown(),
    )
