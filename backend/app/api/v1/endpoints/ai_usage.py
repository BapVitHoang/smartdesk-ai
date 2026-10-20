"""AI Usage Observability & Telemetry Endpoints (REQ-22, REQ-33)."""

import logging
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func
from pydantic import BaseModel

from app.db.session import get_db
from app.models.ai_usage import AIUsageLog
from app.core.deps import require_role

logger = logging.getLogger("smartdesk.api.ai_usage")

router = APIRouter()


class AIUsageSummaryResponse(BaseModel):
    """Aggregated KPIs for AI cost, token, and latency observability."""
    total_requests: int
    success_count: int
    fallback_count: int
    refused_count: int
    error_count: int
    total_input_tokens: int
    total_output_tokens: int
    total_cost_usd: float
    avg_latency_ms: float
    recent_logs: List[Dict[str, Any]]


@router.get(
    "",
    response_model=AIUsageSummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Get AI Usage & Cost Observability Summary",
    description="Returns aggregated metrics on AI request count, token consumption, cost in USD, and recent telemetry logs."
)
async def get_ai_usage_summary(
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _admin: Any = Depends(require_role("admin"))
) -> AIUsageSummaryResponse:
    """Retrieves AI observability summary and recent request logs."""
    # Query recent logs
    result = await db.execute(
        select(AIUsageLog).order_by(desc(AIUsageLog.created_at)).limit(limit)
    )
    logs = result.scalars().all()

    # Query totals
    total_res = await db.execute(select(func.count(AIUsageLog.id)))
    total_count = total_res.scalar() or 0

    success_res = await db.execute(select(func.count(AIUsageLog.id)).where(AIUsageLog.status == "success"))
    success_count = success_res.scalar() or 0

    fallback_res = await db.execute(select(func.count(AIUsageLog.id)).where(AIUsageLog.status == "fallback"))
    fallback_count = fallback_res.scalar() or 0

    refused_res = await db.execute(select(func.count(AIUsageLog.id)).where(AIUsageLog.status == "refused"))
    refused_count = refused_res.scalar() or 0

    cost_res = await db.execute(select(func.sum(AIUsageLog.cost_usd)))
    total_cost = round(cost_res.scalar() or 0.0, 6)

    latency_res = await db.execute(select(func.avg(AIUsageLog.latency_ms)))
    avg_latency = round(latency_res.scalar() or 0.0, 2)

    in_tokens_res = await db.execute(select(func.sum(AIUsageLog.input_tokens)))
    total_in = in_tokens_res.scalar() or 0

    out_tokens_res = await db.execute(select(func.sum(AIUsageLog.output_tokens)))
    total_out = out_tokens_res.scalar() or 0

    return AIUsageSummaryResponse(
        total_requests=total_count,
        success_count=success_count,
        fallback_count=fallback_count,
        refused_count=refused_count,
        error_count=max(0, total_count - success_count - fallback_count - refused_count),
        total_input_tokens=total_in,
        total_output_tokens=total_out,
        total_cost_usd=total_cost,
        avg_latency_ms=avg_latency,
        recent_logs=[
            {
                "id": log.id,
                "endpoint": log.endpoint,
                "prompt_version": log.prompt_version,
                "provider": log.provider,
                "model_name": log.model_name,
                "tools_called": log.tools_called,
                "input_tokens": log.input_tokens,
                "output_tokens": log.output_tokens,
                "total_tokens": log.total_tokens,
                "cost_usd": log.cost_usd,
                "latency_ms": log.latency_ms,
                "status": log.status,
                "created_at": log.created_at.isoformat() if log.created_at else None,
            }
            for log in logs
        ]
    )
