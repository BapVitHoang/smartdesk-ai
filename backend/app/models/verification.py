"""Verification ORM models for Active Knowledge Verification Engine."""

from datetime import datetime, timezone
from typing import List, Optional, TYPE_CHECKING
from sqlalchemy import String, Text, Integer, Float, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.document import Document


def utc_now() -> datetime:
    """Return timezone-aware current UTC datetime."""
    return datetime.now(timezone.utc)


class VerificationReport(Base):
    """Aggregate assessment report for a verified document."""

    __tablename__ = "verification_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    document_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("documents.id"), index=True, nullable=False
    )
    workspace_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("workspaces.id"), index=True, nullable=False
    )
    faithfulness_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="passed",
        doc="passed | warning | failed",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    document: Mapped["Document"] = relationship("Document", back_populates="verification_report")
    items: Mapped[List["VerificationItem"]] = relationship(
        "VerificationItem", back_populates="report", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<VerificationReport doc_id={self.document_id} score={self.faithfulness_score} status={self.status}>"


class VerificationItem(Base):
    """Individual synthetic test item within a verification report."""

    __tablename__ = "verification_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    report_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("verification_reports.id"), index=True, nullable=False
    )
    question: Mapped[str] = mapped_column(Text, nullable=False)
    ground_truth: Mapped[str] = mapped_column(Text, nullable=False)
    rag_answer: Mapped[str] = mapped_column(Text, nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="passed",
        doc="passed | warning | failed",
    )
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    report: Mapped["VerificationReport"] = relationship("VerificationReport", back_populates="items")

    def __repr__(self) -> str:
        return f"<VerificationItem id={self.id} score={self.score} status={self.status}>"
