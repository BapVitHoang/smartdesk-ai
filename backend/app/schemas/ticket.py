"""Ticket request and response Pydantic schemas."""

from datetime import datetime
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class TicketPriorityEnum(str, Enum):
    """Urgency / Priority levels strictly constrained to 4 values."""
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    URGENT = "Urgent"


class TicketStatusEnum(str, Enum):
    """Ticket lifecycle states."""
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"


class TicketCategoryEnum(str, Enum):
    """Standard support ticket categories."""
    AUTHENTICATION = "Authentication"
    BILLING = "Billing"
    TECHNICAL_BUG = "Technical Bug"
    FEATURE_REQUEST = "Feature Request"
    GENERAL = "General"


class TicketCreate(BaseModel):
    """Schema for customer ticket submission or escalation."""

    customer_name: str = Field(
        ...,
        min_length=2,
        max_length=128,
        description="Full name of the customer",
        examples=["Nguyen Van A"]
    )
    customer_email: EmailStr = Field(
        ...,
        description="Valid email address for ticket updates and notifications",
        examples=["nguyenvana@example.com"]
    )
    category: str = Field(
        ...,
        min_length=2,
        max_length=64,
        description="Issue category (e.g., Authentication, Billing, Technical Bug)",
        examples=["Authentication"]
    )
    priority: TicketPriorityEnum = Field(
        default=TicketPriorityEnum.MEDIUM,
        description="Urgency level: Low, Medium, High, or Urgent",
        examples=["Urgent"]
    )
    subject: str = Field(
        ...,
        min_length=5,
        max_length=255,
        description="Brief subject summarizing the problem",
        examples=["Lost 2FA recovery token for corporate account"]
    )
    description: str = Field(
        ...,
        min_length=15,
        max_length=5000,
        description="Detailed problem explanation",
        examples=["I changed my phone number and lost access to the authenticator app. Need help resetting."]
    )


class TicketUpdate(BaseModel):
    """Schema for updating ticket status or editing AI draft reply."""

    status: Optional[TicketStatusEnum] = Field(
        default=None,
        description="Updated lifecycle status: open, in_progress, resolved, or closed",
        examples=["in_progress"]
    )
    ai_draft_reply: Optional[str] = Field(
        default=None,
        description="Agent-customized or approved reply content",
        examples=["Dear Nguyen Van A, We have reviewed your request..."]
    )
    category: Optional[str] = Field(
        default=None,
        description="Updated ticket category",
        examples=["Authentication"]
    )
    priority: Optional[TicketPriorityEnum] = Field(
        default=None,
        description="Updated priority level",
        examples=["Urgent"]
    )


class TicketResponse(BaseModel):
    """Full ticket representation returned by API."""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Unique integer primary key", examples=[1042])
    ticket_code: str = Field(..., description="Formatted ticket identifier", examples=["#TICK-1042"])
    customer_name: str = Field(..., description="Customer full name")
    customer_email: str = Field(..., description="Customer email address")
    category: str = Field(..., description="Ticket category")
    priority: str = Field(..., description="Ticket priority (Low, Medium, High, Urgent)")
    subject: str = Field(..., description="Ticket subject line")
    description: str = Field(..., description="Full issue description")
    status: str = Field(..., description="Current status (open, in_progress, resolved, closed)")
    ai_tags: List[str] = Field(
        default_factory=list,
        description="Automated AI triage tags",
        examples=[["Authentication", "Urgent", "2FA Recovery"]]
    )
    ai_draft_reply: Optional[str] = Field(
        default=None,
        description="Pre-drafted resolution from AI Copilot"
    )
    estimated_response_hours: int = Field(
        ...,
        description="SLA estimated response time in hours",
        examples=[2]
    )
    created_at: datetime = Field(..., description="Timestamp when ticket was created")
    updated_at: Optional[datetime] = Field(default=None, description="Timestamp of last update")


class TicketFilter(BaseModel):
    """Filter parameters for listing tickets in the Agent Triage Dashboard."""

    status: Optional[str] = None
    category: Optional[str] = None
    priority: Optional[str] = None
    search: Optional[str] = None
    skip: int = Field(default=0, ge=0)
    limit: int = Field(default=20, ge=1, le=100)
