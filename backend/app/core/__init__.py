"""Core configurations, security guardrails, and exceptions."""

from app.core.config import settings
from app.core.exceptions import SmartDeskException

__all__ = ["settings", "SmartDeskException"]
