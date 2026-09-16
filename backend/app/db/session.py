"""Async Database session configuration and lifecycle initialization."""

from typing import AsyncGenerator
import json
import logging
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker,
    AsyncEngine
)
from sqlalchemy import select

from app.core.config import settings
from app.db.base import Base

logger = logging.getLogger("smartdesk.db")


def normalize_database_url(url: str) -> str:
    """Ensure database connection URL uses an asynchronous driver."""
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+asyncpg://", 1)
    if url.startswith("sqlite:///") and not url.startswith("sqlite+aiosqlite:///"):
        return url.replace("sqlite:///", "sqlite+aiosqlite:///", 1)
    return url


db_url = normalize_database_url(settings.DATABASE_URL)

# Configure Async Engine with appropriate pooling
engine_kwargs = {"echo": settings.DEBUG}
if "sqlite" in db_url:
    engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    engine_kwargs["pool_pre_ping"] = True
    engine_kwargs["pool_size"] = 10
    engine_kwargs["max_overflow"] = 20

engine: AsyncEngine = create_async_engine(db_url, **engine_kwargs)

async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI Dependency providing an async database session."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """Initialize database tables and seed initial FAQ data if empty."""
    # Import models here to ensure they register with Base.metadata
    from app.models.ticket import Ticket  # noqa: F401
    from app.models.knowledge import FAQItem  # noqa: F401

    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database schema synchronized successfully.")

        # Seed initial FAQ items if table is empty
        async with async_session_factory() as session:
            result = await session.execute(select(FAQItem).limit(1))
            existing_faq = result.scalars().first()

            if not existing_faq:
                faq_path = settings.resolved_seed_faq_path
                if faq_path.exists():
                    logger.info(f"Seeding initial FAQ knowledge from {faq_path}...")
                    with open(faq_path, "r", encoding="utf-8") as f:
                        faq_records = json.load(f)

                    for item in faq_records:
                        faq_obj = FAQItem(
                            doc_id=item.get("doc_id", ""),
                            category=item.get("category", "General"),
                            title=item.get("title", ""),
                            content=item.get("content", ""),
                            source_url=item.get("source_url", "")
                        )
                        session.add(faq_obj)

                    await session.commit()
                    logger.info(f"Successfully seeded {len(faq_records)} FAQ articles.")
                else:
                    logger.warning(f"Seed file not found at {faq_path}. Skipping initial seeding.")

            # Seed initial Tickets if empty
            ticket_result = await session.execute(select(Ticket).limit(1))
            existing_ticket = ticket_result.scalars().first()
            if not existing_ticket:
                logger.info("Seeding initial support tickets...")
                sample_tickets = [
                    Ticket(
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
    except Exception as e:
        logger.error(f"Error during database initialization: {e}", exc_info=True)
        # For non-fatal database initialization failure, allow fallback
