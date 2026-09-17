"""Consolidated APIRouter for API Version 1."""

from fastapi import APIRouter

from app.api.v1.endpoints import chat, tickets, agent, health, knowledge

api_router = APIRouter()

api_router.include_router(chat.router, prefix="/chat", tags=["Chat & RAG"])
api_router.include_router(tickets.router, prefix="/tickets", tags=["Tickets & Triage"])
api_router.include_router(agent.router, prefix="/agent", tags=["Agent Copilot"])
api_router.include_router(knowledge.router, prefix="/knowledge", tags=["Knowledge Base"])
api_router.include_router(health.router, prefix="/health", tags=["Health & Benchmarks"])
