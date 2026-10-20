"""Consolidated APIRouter for API Version 1 with conflict-free optional module discovery."""

import importlib
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
)

logger = logging.getLogger("smartdesk.api")

api_router = APIRouter()

# Core frozen v1 routes
api_router.include_router(chat.router, prefix="/chat", tags=["Chat & RAG"])
api_router.include_router(tickets.router, prefix="/tickets", tags=["Tickets & Triage"])
api_router.include_router(agent.router, prefix="/agent", tags=["Agent Copilot"])
api_router.include_router(knowledge.router, prefix="/knowledge", tags=["Knowledge Base"])
api_router.include_router(health.router, prefix="/health", tags=["Health & Benchmarks"])
api_router.include_router(workspaces.router, prefix="/workspaces", tags=["Workspaces"])
api_router.include_router(documents.router, prefix="", tags=["Documents & Verification"])

# Conflict-free extension point: auto-mount optional feature routers when created by module owners
OPTIONAL_EXTENSION_ROUTERS = [
    ("app.api.v1.endpoints.auth", "/auth", ["Auth & RBAC"]),
    ("app.api.v1.endpoints.telemetry", "/admin", ["AI Telemetry & Evaluation"]),
]

for module_path, route_prefix, route_tags in OPTIONAL_EXTENSION_ROUTERS:
    try:
        mod = importlib.import_module(module_path)
        ext_router = getattr(mod, "router", None)
        if ext_router is not None:
            api_router.include_router(ext_router, prefix=route_prefix, tags=route_tags)
    except ModuleNotFoundError:
        pass
    except Exception as exc:
        logger.warning(f"Optional router '{module_path}' could not be mounted: {exc}")
