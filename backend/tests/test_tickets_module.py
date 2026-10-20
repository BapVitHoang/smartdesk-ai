"""Dedicated module test suite for Owner 2 (Tickets, SLA Calculation & Canonical Categories)."""

import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.schemas.ticket import CANONICAL_TICKET_CATEGORIES, TicketCategoryEnum, TicketPriorityEnum
from app.services.ticket_service import ticket_service


def test_canonical_sla_hours_mapping() -> None:
    """Verify SLA hours match the frozen contract (Urgent=2, High=4, Medium=8, Low=24)."""
    assert ticket_service.calculate_sla_hours("Urgent") == 2
    assert ticket_service.calculate_sla_hours("High") == 4
    assert ticket_service.calculate_sla_hours("Medium") == 8
    assert ticket_service.calculate_sla_hours("Low") == 24


def test_canonical_ticket_categories_and_alias() -> None:
    """Verify both Bug Report (canonical) and Technical Bug (alias) are supported."""
    assert "Bug Report" in CANONICAL_TICKET_CATEGORIES
    assert TicketCategoryEnum.BUG_REPORT.value == "Bug Report"
    assert TicketCategoryEnum.TECHNICAL_BUG.value == "Technical Bug"
    assert TicketPriorityEnum.URGENT.value == "Urgent"
