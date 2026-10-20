"""Consolidated APIRouter for API Version 1 with frozen interfaces and pre-registered routers."""

import logging
from fastapi import APIRouter

from app.api.v1.endpoints import (
    chat,
    tickets,
    agent,
    health,
    knowledge,
    workspaces,
    documents,
    auth,
    ai_usage,
    chat_stream,
    chat_actions,
)

logger = logging.getLogger("smartdesk.api")

api_router = APIRouter()

# Core frozen v1 routes
api_router.include_router(chat.router, prefix="/chat", tags=["Chat & RAG"])
api_router.include_router(chat_stream.router, prefix="/chat", tags=["Chat & Streaming"])
api_router.include_router(chat_actions.router, prefix="/chat", tags=["Chat & Agent Tools"])
api_router.include_router(tickets.router, prefix="/tickets", tags=["Tickets & Triage"])
api_router.include_router(agent.router, prefix="/agent", tags=["Agent Copilot"])
api_router.include_router(ai_usage.router, prefix="/agent/ai-usage", tags=["AI Telemetry & Observability"])
api_router.include_router(knowledge.router, prefix="/knowledge", tags=["Knowledge Base"])
api_router.include_router(health.router, prefix="/health", tags=["Health & Benchmarks"])
api_router.include_router(workspaces.router, prefix="/workspaces", tags=["Workspaces"])
api_router.include_router(documents.router, prefix="", tags=["Documents & Verification"])
api_router.include_router(auth.router, prefix="/auth", tags=["Auth & RBAC"])
