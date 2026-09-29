"""Knowledge base and FAQ ORM models."""

from datetime import datetime, timezone
from typing import List, Optional, TYPE_CHECKING
from sqlalchemy import String, Text, Integer, DateTime, JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.document import Document


def utc_now() -> datetime:
    """Return timezone-aware current UTC datetime."""
    return datetime.now(timezone.utc)


class FAQItem(Base):
    """Curated knowledge base / FAQ item model for RAG and fallback retrieval."""

    __tablename__ = "faq_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    doc_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    category: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    source_url: Mapped[str] = mapped_column(String(255), nullable=False)
    embedding: Mapped[Optional[List[float]]] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    def __repr__(self) -> str:
        return f"<FAQItem doc_id={self.doc_id} title={self.title[:30]}>"


class KnowledgeChunk(Base):
    """Fine-grained vector chunk for enterprise RAG synthesizer."""

    __tablename__ = "knowledge_chunks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    chunk_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    parent_doc_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False, default="doc-default")
    workspace_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True, default=1)
    document_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("documents.id"), nullable=True, index=True
    )
    chunk_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    page_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    source_url: Mapped[str] = mapped_column(String(255), nullable=False)
    embedding: Mapped[Optional[List[float]]] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    document: Mapped[Optional["Document"]] = relationship("Document", back_populates="chunks")
