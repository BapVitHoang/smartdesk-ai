"""Seed initial AI usage telemetry records for Admin Observability Dashboard (REQ-22, REQ-33)."""

import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai_usage import AIUsageLog

logger = logging.getLogger("smartdesk.seed.ai_usage")


async def seed_ai_usage(session: AsyncSession) -> None:
    """Seeds baseline AI usage telemetry logs if ai_usage_logs table is empty."""
    res = await session.execute(select(AIUsageLog).limit(1))
    if res.scalars().first():
        return

    sample_logs = [
        AIUsageLog(
            endpoint="/api/v1/chat",
            prompt_version="rag_customer_support@v1.0.0",
            provider="gemini",
            model_name="gemini-3.5-flash-lite",
            tools_called=[],
            input_tokens=420,
            output_tokens=185,
            total_tokens=605,
            cost_usd=round((420 * 0.30 + 185 * 2.50) / 1_000_000, 6),
            latency_ms=920.5,
            status="success",
            workspace_id=1,
        ),
        AIUsageLog(
            endpoint="/api/v1/tickets",
            prompt_version="ticket_copilot_draft@v1.0.0",
            provider="gemini",
            model_name="gemini-3.5-flash-lite",
            tools_called=[],
            input_tokens=310,
            output_tokens=140,
            total_tokens=450,
            cost_usd=round((310 * 0.30 + 140 * 2.50) / 1_000_000, 6),
            latency_ms=680.2,
            status="success",
            workspace_id=1,
        ),
        AIUsageLog(
            endpoint="/api/v1/chat",
            prompt_version="guardrail_precheck",
            provider="local",
            model_name="regex_guardrail",
            tools_called=[],
            input_tokens=45,
            output_tokens=0,
            total_tokens=45,
            cost_usd=0.0,
            latency_ms=2.1,
            status="refused",
            workspace_id=1,
        ),
    ]

    for item in sample_logs:
        session.add(item)
    await session.commit()
    logger.info(f"Seeded {len(sample_logs)} baseline AI usage telemetry logs.")
