"""SQLAlchemy ORM models package."""

from app.models.ticket import Ticket
from app.models.knowledge import FAQItem, KnowledgeChunk

__all__ = ["Ticket", "FAQItem", "KnowledgeChunk"]
