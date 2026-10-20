"""Seed initial customer support tickets for Agent Triage Dashboard."""

import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ticket import Ticket

logger = logging.getLogger("smartdesk.seed.tickets")


async def seed_tickets(session: AsyncSession) -> None:
    """Seeds initial tickets (#TICK-1042, #TICK-1041, #TICK-1039) if tickets table is empty."""
    ticket_result = await session.execute(select(Ticket).limit(1))
    if ticket_result.scalars().first():
        return

    logger.info("Seeding initial support tickets...")
    sample_tickets = [
        Ticket(
            workspace_id=1,
            ticket_code="#TICK-1042",
            customer_name="Nguyễn Văn An",
            customer_email="an.nguyen@company.vn",
            category="Billing",
            priority="High",
            subject="Lỗi thanh toán cổng VNPAY đơn hàng #9842",
            description="Tôi đã quét mã QR thanh toán thành công lúc 10:15, tài khoản trừ 1.500.000đ nhưng trang giỏ hàng báo Timeout. Mong hỗ trợ kiểm tra gấp.",
            status="open",
            ai_tags=["Billing", "High", "Invoice & Billing", "Network Timeout"],
            ai_draft_reply="Chào anh An, SmartDesk AI đã xác thực mã giao dịch của anh trên cổng VNPAY. Hệ thống đã đối soát thành công và tiến hành kích hoạt đơn hàng #9842 ngay cho anh trong vòng 5 phút tới.",
            estimated_response_hours=4
        ),
        Ticket(
            workspace_id=1,
            ticket_code="#TICK-1041",
            customer_name="Trần Mai Anh",
            customer_email="maianh.tran@tech.io",
            category="Authentication",
            priority="Urgent",
            subject="Không thể nhận email OTP đặt lại mật khẩu 2FA",
            description="Tôi cần truy cập tài khoản admin để duyệt hợp đồng gấp nhưng bấm gửi lại OTP 5 lần đều không nhận được mail.",
            status="in_progress",
            ai_tags=["Authentication", "Urgent", "2FA Recovery", "Password Reset"],
            ai_draft_reply="Chào chị Mai Anh, bộ phận kỹ thuật đã kiểm tra mail server của domain @tech.io bị chặn filter tạm thời. SmartDesk đã kích hoạt phương thức phục hồi phụ qua SMS xác thực tới số điện thoại đuôi **789.",
            estimated_response_hours=2
        ),
        Ticket(
            workspace_id=1,
            ticket_code="#TICK-1039",
            customer_name="Lê Hoàng Quân",
            customer_email="quan.le@startup.co",
            category="Feature Request",
            priority="Low",
            subject="Đề xuất tính năng Export báo cáo CSV tùy biến",
            description="Hiện tại hệ thống chỉ cho tải PDF tổng hợp tháng, mong muốn có thêm nút Export CSV theo tuần.",
            status="resolved",
            ai_tags=["Feature Request", "Low"],
            ai_draft_reply="Cảm ơn đóng góp của anh Quân. Tính năng tùy biến Export báo cáo đã được đưa vào Roadmap phiên bản Sprint Q3.",
            estimated_response_hours=24
        )
    ]
    for t in sample_tickets:
        session.add(t)
    await session.commit()
    logger.info(f"Successfully seeded {len(sample_tickets)} initial support tickets.")
