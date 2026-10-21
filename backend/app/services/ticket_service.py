"""Ticket lifecycle management, SLA estimation, auto-tagging, and AI Copilot drafting."""

import re
import logging
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.ticket import Ticket
from app.schemas.ticket import TicketCreate
from app.services.ticket_copilot_service import ticket_copilot_service

logger = logging.getLogger("smartdesk.ticket_service")


class TicketService:
    """Business logic for support ticket processing, triage tagging, and draft generation."""

    def calculate_sla_hours(self, priority: str) -> int:
        """Determines expected response SLA hours according to urgency level."""
        mapping = {
            "Urgent": 2,
            "High": 4,
            "Medium": 8,
            "Low": 24
        }
        return mapping.get(priority, 8)

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
        description: str,
        workspace_id: Optional[int] = 1,
        db: Optional[AsyncSession] = None
    ) -> str:
        """
        Generates a professional, empathetic draft resolution using TicketCopilotService single-call
        structured output aligned with workspace persona and business rules.
        """
        try:
            copilot_output = await ticket_copilot_service.generate_ticket_triage_and_draft(
                subject=subject,
                description=description,
                workspace_id=workspace_id or 1,
                session=db,
                customer_name=customer_name,
                category_hint=category,
                priority_hint=priority,
            )
            if copilot_output and copilot_output.ai_draft_reply and len(copilot_output.ai_draft_reply.strip()) > 30:
                return copilot_output.ai_draft_reply.strip()
        except Exception as exc:
            logger.warning(f"TicketCopilot draft generation encountered error: {exc}")

        # Deterministic template fallback in Vietnamese (AGENTS.md & PLAN.md)
        sla_hours = self.calculate_sla_hours(priority)
        ws_name = "SmartDesk Cloud Support"
        persona_name = "SmartDesk Support Specialist"
        return (
            f"Kính gửi {customer_name},\n\n"
            f"Cảm ơn quý khách đã liên hệ với {ws_name}. Chúng tôi đã tiếp nhận yêu cầu liên quan đến \"{subject}\" "
            f"và phân loại yêu cầu vào danh mục [{category}] với mức độ ưu tiên [{priority}].\n\n"
            f"Chính sách hỗ trợ cho danh mục {category}:\n"
            f"1. Đội ngũ chuyên trách đang tiến hành rà soát chi tiết yêu cầu của quý khách.\n"
            f"2. Nếu có thêm ảnh chụp màn hình, mã lỗi hoặc chứng từ giao dịch, quý khách vui lòng phản hồi trực tiếp vào phiếu này.\n"
            f"3. Quý khách sẽ nhận được phản hồi từ chuyên viên trong khung cam kết SLA {sla_hours} giờ.\n\n"
            f"Rất cảm ơn sự kiên nhẫn của quý khách.\n\n"
            f"Trân trọng,\n"
            f"{persona_name} - {ws_name}"
        )

    async def create_ticket(self, db: AsyncSession, ticket_in: TicketCreate) -> Ticket:
        """
        Creates a new ticket, assigns #TICK-XXXX code, auto-tags, and pre-populates AI draft
        using single-call ticket copilot structured output (REQ-15).
        """
        # Determine next sequence number by finding max existing code to avoid collision with seed data
        result = await db.execute(select(Ticket.ticket_code))
        existing_codes = result.scalars().all()
        max_num = 1000
        for code in existing_codes:
            m = re.search(r"(\d+)$", code)
            if m:
                val = int(m.group(1))
                if val > max_num:
                    max_num = val
        sequence_num = max(max_num + 1, 1001)
        ticket_code = f"#TICK-{sequence_num}"
        existing_set = set(existing_codes)
        while ticket_code in existing_set:
            sequence_num += 1
            ticket_code = f"#TICK-{sequence_num}"

        ws_id = ticket_in.workspace_id or 1

        # Calculate SLA response hours
        sla_hours = self.calculate_sla_hours(ticket_in.priority.value)

        # 1. Single-call copilot structured triage and localized draft generation
        try:
            copilot_output = await ticket_copilot_service.generate_ticket_triage_and_draft(
                subject=ticket_in.subject,
                description=ticket_in.description,
                workspace_id=ws_id,
                session=db,
                customer_name=ticket_in.customer_name,
                category_hint=ticket_in.category,
                priority_hint=ticket_in.priority.value,
            )
            ai_tags = copilot_output.ai_tags if copilot_output and copilot_output.ai_tags else self.extract_ai_tags(
                category=ticket_in.category,
                priority=ticket_in.priority.value,
                subject=ticket_in.subject,
                description=ticket_in.description
            )
            ai_draft = copilot_output.ai_draft_reply if copilot_output and copilot_output.ai_draft_reply else await self.generate_draft_reply(
                customer_name=ticket_in.customer_name,
                category=ticket_in.category,
                priority=ticket_in.priority.value,
                subject=ticket_in.subject,
                description=ticket_in.description,
                workspace_id=ws_id,
                db=db
            )
        except Exception as e:
            logger.warning(f"Error in ticket copilot triage, falling back to rule-based tags and draft: {e}")
            ai_tags = self.extract_ai_tags(
                category=ticket_in.category,
                priority=ticket_in.priority.value,
                subject=ticket_in.subject,
                description=ticket_in.description
            )
            ai_draft = await self.generate_draft_reply(
                customer_name=ticket_in.customer_name,
                category=ticket_in.category,
                priority=ticket_in.priority.value,
                subject=ticket_in.subject,
                description=ticket_in.description,
                workspace_id=ws_id,
                db=db
            )

        db_ticket = Ticket(
            workspace_id=ticket_in.workspace_id or 1,
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
