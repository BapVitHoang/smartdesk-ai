"""Ticket ORM model definition."""

from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy import String, Text, Integer, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def utc_now() -> datetime:
    """Return timezone-aware current UTC datetime."""
    return datetime.now(timezone.utc)


class Ticket(Base):
    """Support Ticket ORM Model with AI triage copilot attributes."""

    __tablename__ = "tickets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticket_code: Mapped[str] = mapped_column(
        String(32), unique=True, index=True, nullable=False, doc="Formatted ticket ID (e.g. #TICK-1042)"
    )
    customer_name: Mapped[str] = mapped_column(String(128), nullable=False)
    customer_email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    priority: Mapped[str] = mapped_column(
        String(32), nullable=False, index=True, doc="Strictly: Low, Medium, High, Urgent"
    )
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String(32), default="open", nullable=False, index=True, doc="open, in_progress, resolved, closed"
    )
    ai_tags: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    ai_draft_reply: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    estimated_response_hours: Mapped[int] = mapped_column(Integer, default=24, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    def __repr__(self) -> str:
        return f"<Ticket code={self.ticket_code} status={self.status} priority={self.priority}>"
