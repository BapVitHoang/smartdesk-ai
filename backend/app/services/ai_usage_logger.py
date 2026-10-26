"""AI Usage Telemetry Logger Service (REQ-22, REQ-33)."""

import logging
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import async_session_factory
from app.models.ai_usage import AIUsageLog

logger = logging.getLogger("smartdesk.ai_usage_logger")


async def log_ai_call(
    endpoint: str,
    prompt_version: str,
    provider: str,
    model_name: str,
    tools_called: Optional[List[str]] = None,
    input_tokens: int = 0,
    output_tokens: int = 0,
    cost_usd: float = 0.0,
    latency_ms: float = 0.0,
    status: str = "success",
    workspace_id: int = 1,
    session: Optional[AsyncSession] = None,
) -> None:
    """
    Persists an AI request execution event into the ai_usage_logs table.
    Works either with an active database session or opens an isolated session.
    """
    total_tokens = input_tokens + output_tokens
    tools_list = tools_called or []

    log_entry = AIUsageLog(
        endpoint=endpoint,
        prompt_version=prompt_version,
        provider=provider,
        model_name=model_name,
        tools_called=tools_list,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=total_tokens,
        cost_usd=cost_usd,
        latency_ms=latency_ms,
        status=status,
        workspace_id=workspace_id,
    )

    try:
        if session:
            session.add(log_entry)
            await session.commit()
        else:
            async with async_session_factory() as local_session:
                local_session.add(log_entry)
                await local_session.commit()
    except Exception as exc:
        logger.warning(f"Failed to record AI usage log: {exc}")
