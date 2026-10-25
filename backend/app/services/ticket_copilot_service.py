"""Single-Call Ticket Copilot Service using Pydantic v2 Structured Output (Capability C - REQ-15)."""

import logging
import time
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.prompts import prompt_registry
from app.models.workspace import Workspace
from app.schemas.ai_structured import TicketCopilotStructuredOutput
from app.services.ai_usage_logger import log_ai_call
from app.services.fallback_service import fallback_service
from app.services.llm_service import LLMConfigException, llm_service

logger = logging.getLogger("smartdesk.ticket_copilot")


class TicketCopilotService:
    """Single-call LLM structured output service for ticket triage, tagging, sentiment, and Vietnamese draft generation."""

    SLA_MAP = {
        "Urgent": 2,
        "High": 4,
        "Medium": 8,
        "Low": 24,
    }

    def infer_category(self, text: str, category_hint: Optional[str] = None) -> str:
        """Infers canonical ticket category from text or normalizes hint."""
        if category_hint:
            if category_hint == "Technical Bug":
                return "Bug Report"
            if category_hint in {"Authentication", "Billing", "Bug Report", "Feature Request", "General"}:
                return category_hint

        low = text.lower()
        if any(k in low for k in ["2fa", "mfa", "password", "mật khẩu", "sso", "login", "đăng nhập", "otp"]):
            return "Authentication"
        if any(k in low for k in ["invoice", "hóa đơn", "refund", "hoàn tiền", "vnpay", "billing", "thanh toán", "trừ tiền"]):
            return "Billing"
        if any(k in low for k in ["bug", "lỗi", "crash", "500", "429", "timeout", "treo", "không hoạt động", "webhook"]):
            return "Bug Report"
        if any(k in low for k in ["feature", "tính năng", "đề xuất", "export", "bổ sung", "nâng cấp"]):
            return "Feature Request"
        return "General"

    def infer_priority(self, text: str, priority_hint: Optional[str] = None) -> str:
        """Infers priority level from urgency cues or hint."""
        if priority_hint and priority_hint.capitalize() in {"Low", "Medium", "High", "Urgent"}:
            return priority_hint.capitalize()

        low = text.lower()
        if any(k in low for k in ["urgent", "khẩn cấp", "sập", "outage", "nghiêm trọng", "mất tiền", "production down"]):
            return "Urgent"
        if any(k in low for k in ["high", "gấp", "không đăng nhập được", "403", "429", "bảo mật", "security"]):
            return "High"
        if any(k in low for k in ["low", "hỏi thêm", "tư vấn", "góp ý"]):
            return "Low"
        return "Medium"

    def infer_sentiment(self, text: str, priority: str) -> str:
        """Infers customer sentiment from message tone."""
        low = text.lower()
        if priority == "Urgent" or any(k in low for k in ["khẩn cấp", "ngay lập tức", "urgent", "cấp cứu"]):
            return "urgent"
        if any(k in low for k in ["bức xúc", "tệ", "thất vọng", "quá lâu", "lỗi hoài", "frustrated", "angry"]):
            return "frustrated"
        if any(k in low for k in ["cảm ơn", "hài lòng", "tốt", "tuyệt vời"]):
            return "positive"
        return "neutral"

    def extract_tags(self, category: str, priority: str, text: str) -> List[str]:
        """Extracts up to 5 relevant technical and domain tags."""
        tags: List[str] = [category, priority]
        low = text.lower()
        keyword_tag_rules = [
            ("2fa", "2FA Recovery"),
            ("mfa", "MFA Security"),
            ("password", "Password Reset"),
            ("mật khẩu", "Password Reset"),
            ("refund", "Refund Request"),
            ("hoàn tiền", "Refund Request"),
            ("invoice", "Invoice & Billing"),
            ("hóa đơn", "Invoice & Billing"),
            ("vnpay", "VNPAY Gateway"),
            ("429", "Rate Limit 429"),
            ("webhook", "Webhook Issue"),
            ("sso", "SSO / SAML"),
            ("token", "API Token"),
            ("timeout", "Network Timeout"),
            ("nha khoa", "Dental Care"),
            ("tẩy trắng", "Laser Whitening"),
            ("bảo hành", "Warranty Policy"),
            ("đổi trả", "Return Policy"),
        ]
        for kw, tag_label in keyword_tag_rules:
            if kw in low and tag_label not in tags:
                tags.append(tag_label)
        return tags[:5]

    async def generate_ticket_triage_and_draft(
        self,
        subject: str,
        description: str,
        workspace_id: int = 1,
        session: Optional[AsyncSession] = None,
        customer_name: str = "Quý khách",
        category_hint: Optional[str] = None,
        priority_hint: Optional[str] = None,
    ) -> TicketCopilotStructuredOutput:
        """
        Invokes LLM single-call structured output to triage the ticket (category, priority, ai_tags, sentiment, summary)
        and produce a natural Vietnamese customer-facing draft reply.
        Falls back to deterministic rule-based output if LLM service is offline or in cooldown.
        """
        start_time = time.perf_counter()
        ws_id = workspace_id or 1

        ws_name = "SmartDesk Cloud Support"
        persona_name = "SmartDesk Support Specialist"
        industry = "IT & SaaS"
        tone_of_voice = "Chuyên nghiệp, ngắn gọn, thân thiện và chính xác về mặt kỹ thuật."
        business_rules = "Luôn bảo vệ an toàn thông tin khách hàng và tuân thủ cam kết SLA."

        if session and ws_id:
            try:
                ws_res = await session.execute(select(Workspace).where(Workspace.id == ws_id))
                ws = ws_res.scalar_one_or_none()
                if ws:
                    ws_name = ws.name
                    persona_name = ws.persona_name
                    industry = ws.industry
                    tone_of_voice = ws.tone_of_voice
                    business_rules = ws.business_rules
            except Exception as exc:
                logger.warning(f"Failed to query workspace {ws_id} in TicketCopilotService: {exc}")

        combined_text = f"{subject} {description}".strip()
        matched = fallback_service.match_faq(
            combined_text,
            workspace_id=ws_id,
            workspace_name=ws_name,
        )
        faq_context = matched.get("response", "") if matched.get("confidence", 0) >= 0.45 else "Không có tài liệu tham chiếu trực tiếp."

        prompt_str = prompt_registry.render(
            "ticket_copilot_structured",
            persona_name=persona_name,
            workspace_name=ws_name,
            industry=industry,
            tone_of_voice=tone_of_voice,
            business_rules=business_rules,
            customer_name=customer_name,
            subject=subject,
            description=description,
            faq_context=faq_context,
        )
        prompt_ver = prompt_registry.get_prompt_version("ticket_copilot_structured")

        fallback_telemetry_status = "fallback"
        if llm_service.is_available() and not llm_service.is_in_cooldown():
            try:
                structured_res, llm_latency = await llm_service.generate_structured_output(
                    prompt=prompt_str,
                    response_model=TicketCopilotStructuredOutput,
                    temperature=0.2,
                )
                await log_ai_call(
                    endpoint="/api/v1/tickets/copilot",
                    prompt_version=prompt_ver,
                    provider=llm_service.provider,
                    model_name=llm_service.active_model_name,
                    tools_called=[],
                    input_tokens=llm_service.last_input_tokens,
                    output_tokens=llm_service.last_output_tokens,
                    cost_usd=llm_service.last_cost_usd,
                    latency_ms=llm_latency,
                    status="success",
                    workspace_id=ws_id,
                    session=session,
                )
                return structured_res
            except LLMConfigException as cfg_err:
                logger.error(f"Single-call structured ticket copilot config error: {cfg_err}")
                fallback_telemetry_status = "config_error"
            except Exception as exc:
                logger.info(f"Single-call structured ticket copilot fallback triggered: {exc}")
                fallback_telemetry_status = "fallback"

        # Deterministic Fallback producing a validated TicketCopilotStructuredOutput
        category = self.infer_category(combined_text, category_hint)
        priority = self.infer_priority(combined_text, priority_hint)
        sentiment = self.infer_sentiment(combined_text, priority)
        ai_tags = self.extract_tags(category, priority, combined_text)
        sla_hours = self.SLA_MAP.get(priority, 8)

        raw_summary = f"[{category}] {subject.strip()}: {description.strip()}"
        if len(raw_summary) < 10:
            raw_summary = f"Yêu cầu hỗ trợ kỹ thuật về {subject.strip() or 'dịch vụ'}"
        summary = raw_summary[:290] + "..." if len(raw_summary) > 290 else raw_summary

        ref_guidance = (
            f"\nHướng dẫn tham khảo nhanh từ hệ thống:\n{faq_context}\n"
            if faq_context and "Không có tài liệu" not in faq_context
            else ""
        )

        draft_reply = (
            f"Kính gửi {customer_name},\n\n"
            f"Cảm ơn quý khách đã liên hệ với {ws_name}. Chúng tôi đã tiếp nhận yêu cầu hỗ trợ về \"{subject}\" "
            f"và phân loại vào danh mục [{category}] với mức độ ưu tiên [{priority}].\n"
            f"{ref_guidance}\n"
            f"Quy trình xử lý tiếp theo:\n"
            f"1. Đội ngũ chuyên trách của {ws_name} đang rà soát chi tiết thông tin kỹ thuật của quý khách.\n"
            f"2. Nếu có thêm ảnh chụp màn hình hoặc mã giao dịch, quý khách vui lòng phản hồi trực tiếp vào phiếu này.\n"
            f"3. Quý khách sẽ nhận được phản hồi chính thức trong khung cam kết SLA tối đa {sla_hours} giờ.\n\n"
            f"Trân trọng,\n"
            f"{persona_name} - {ws_name}"
        )

        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
        await log_ai_call(
            endpoint="/api/v1/tickets/copilot",
            prompt_version=prompt_ver,
            provider="bm25_fallback",
            model_name="deterministic-copilot-v2",
            tools_called=[],
            input_tokens=0,
            output_tokens=0,
            cost_usd=0.0,
            latency_ms=elapsed_ms,
            status=fallback_telemetry_status,
            workspace_id=ws_id,
            session=session,
        )

        return TicketCopilotStructuredOutput(
            category=category,  # type: ignore[arg-type]
            priority=priority,  # type: ignore[arg-type]
            ai_tags=ai_tags,
            sentiment=sentiment,  # type: ignore[arg-type]
            summary=summary,
            ai_draft_reply=draft_reply,
        )


ticket_copilot_service = TicketCopilotService()


async def generate_ticket_triage_and_draft(
    subject: str,
    description: str,
    workspace_id: int = 1,
    session: Optional[AsyncSession] = None,
    customer_name: str = "Quý khách",
    category_hint: Optional[str] = None,
    priority_hint: Optional[str] = None,
) -> TicketCopilotStructuredOutput:
    """Module-level contract function defined in CONTRACTS.md §7."""
    return await ticket_copilot_service.generate_ticket_triage_and_draft(
        subject=subject,
        description=description,
        workspace_id=workspace_id,
        session=session,
        customer_name=customer_name,
        category_hint=category_hint,
        priority_hint=priority_hint,
    )
