"""Ticket lifecycle management, SLA estimation, auto-tagging, and AI Copilot drafting."""

import random
import logging
from typing import List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models.ticket import Ticket
from app.schemas.ticket import TicketCreate
from app.services.llm_service import llm_service
from app.services.fallback_service import fallback_service

logger = logging.getLogger("smartdesk.ticket_service")


class TicketService:
    """Business logic for support ticket processing, triage tagging, and draft generation."""

    def calculate_sla_hours(self, priority: str) -> int:
        """Determines expected response SLA hours according to urgency level."""
        mapping = {
            "Urgent": 2,
            "High": 6,
            "Medium": 12,
            "Low": 24
        }
        return mapping.get(priority, 12)

    def extract_ai_tags(self, category: str, priority: str, subject: str, description: str) -> List[str]:
        """
        Generates contextual AI tags based on category, priority, and detected keywords.
        """
        tags: List[str] = [category, priority]
        combined_text = f"{subject} {description}".lower()

        keyword_tag_rules = [
            ("2fa", "2FA Recovery"),
            ("mfa", "MFA Security"),
            ("password", "Password Reset"),
            ("refund", "Refund Request"),
            ("invoice", "Invoice & Billing"),
            ("429", "Rate Limit 429"),
            ("webhook", "Webhook Issue"),
            ("sso", "SSO / SAML"),
            ("token", "API Token"),
            ("timeout", "Network Timeout"),
            ("mobile", "Mobile Platform"),
            ("security", "Security Incident"),
        ]

        for keyword, tag_name in keyword_tag_rules:
            if keyword in combined_text and tag_name not in tags:
                tags.append(tag_name)

        return tags[:5]

    async def generate_draft_reply(
        self,
        customer_name: str,
        category: str,
        priority: str,
        subject: str,
        description: str
    ) -> str:
        """
        Generates a professional, empathetic draft resolution using LLM or structured template fallback.
        """
        # Search relevant FAQ for grounding the draft
        matched = fallback_service.match_faq(f"{subject} {description}")
        faq_context = matched.get("response", "")

        draft_prompt = (
            f"You are a Senior Customer Support Specialist at SmartDesk AI.\n"
            f"Draft a polite, professional, and empathetic email reply to the customer.\n\n"
            f"Customer Details:\n"
            f"- Name: {customer_name}\n"
            f"- Issue Category: {category}\n"
            f"- Priority: {priority}\n"
            f"- Subject: {subject}\n"
            f"- Description: {description}\n\n"
            f"Knowledge Base Reference:\n{faq_context}\n\n"
            f"Writing Guidelines:\n"
            f"1. Greet the customer warmly by their full name.\n"
            f"2. Acknowledge and summarize their specific concern with empathy.\n"
            f"3. Provide clear step-by-step resolution instructions or explain the next investigative steps.\n"
            f"4. State that their ticket is actively being handled by the support engineering team.\n"
            f"5. Conclude with a warm closing from 'SmartDesk Support Engineering'."
        )

        try:
            draft_text, _ = await llm_service.generate_response(
                prompt=draft_prompt,
                temperature=0.3
            )
            if draft_text and len(draft_text.strip()) > 30:
                return draft_text.strip()
        except Exception as e:
            logger.info(f"LLM draft generation unavailable ({e}). Synthesizing structured template draft.")

        # Deterministic template fallback
        return (
            f"Dear {customer_name},\n\n"
            f"Thank you for contacting SmartDesk AI Support. We have received your inquiry regarding \"{subject}\" "
            f"and our support team has categorized it as [{category}] with [{priority}] priority.\n\n"
            f"Based on our support policies for {category}:\n"
            f"1. Our engineering team is currently verifying the status of your account and system logs.\n"
            f"2. In the meantime, if you have any additional error codes, screenshots, or logs, please reply directly to this thread.\n"
            f"3. You will receive an update from a dedicated specialist within our {self.calculate_sla_hours(priority)}-hour SLA window.\n\n"
            f"We appreciate your patience while we investigate this matter for you.\n\n"
            f"Warm regards,\n"
            f"SmartDesk Support Team"
        )

    async def create_ticket(self, db: AsyncSession, ticket_in: TicketCreate) -> Ticket:
        """
        Creates a new ticket, assigns #TICK-XXXX code, auto-tags, and pre-populates AI draft.
        """
        # Get count to determine next sequence number
        count_result = await db.execute(select(func.count(Ticket.id)))
        current_count = count_result.scalar_one() or 0
        sequence_num = 1001 + current_count

        ticket_code = f"#TICK-{sequence_num}"

        # Calculate SLA response hours
        sla_hours = self.calculate_sla_hours(ticket_in.priority.value)

        # Generate AI tags
        ai_tags = self.extract_ai_tags(
            category=ticket_in.category,
            priority=ticket_in.priority.value,
            subject=ticket_in.subject,
            description=ticket_in.description
        )

        # Generate pre-populated AI draft reply
        ai_draft = await self.generate_draft_reply(
            customer_name=ticket_in.customer_name,
            category=ticket_in.category,
            priority=ticket_in.priority.value,
            subject=ticket_in.subject,
            description=ticket_in.description
        )

        db_ticket = Ticket(
            ticket_code=ticket_code,
            customer_name=ticket_in.customer_name,
            customer_email=str(ticket_in.customer_email),
            category=ticket_in.category,
            priority=ticket_in.priority.value,
            subject=ticket_in.subject,
            description=ticket_in.description,
            status="open",
            ai_tags=ai_tags,
            ai_draft_reply=ai_draft,
            estimated_response_hours=sla_hours
        )

        db.add(db_ticket)
        await db.commit()
        await db.refresh(db_ticket)

        logger.info(f"Created ticket {db_ticket.ticket_code} for {db_ticket.customer_email}")
        return db_ticket


ticket_service = TicketService()
