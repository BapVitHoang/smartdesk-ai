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


def create_engine_and_factory(url: str):
    """Factory helper to build async engine and session factory."""
    norm_url = normalize_database_url(url)
    kwargs = {"echo": settings.DEBUG}
    if "sqlite" in norm_url:
        kwargs["connect_args"] = {"check_same_thread": False}
    else:
        kwargs["pool_pre_ping"] = True
        kwargs["pool_size"] = 10
        kwargs["max_overflow"] = 20

    eng = create_async_engine(norm_url, **kwargs)
    factory = async_sessionmaker(
        bind=eng,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False
    )
    return eng, factory


engine, async_session_factory = create_engine_and_factory(settings.DATABASE_URL)


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
    global engine, async_session_factory
    from app.models.ticket import Ticket  # noqa: F401
    from app.models.knowledge import FAQItem, KnowledgeChunk  # noqa: F401
    from app.models.workspace import Workspace  # noqa: F401
    from app.models.document import Document  # noqa: F401
    from app.models.verification import VerificationReport, VerificationItem  # noqa: F401

    def _migrate_sqlite_columns(sync_conn):
        try:
            ticket_cols = [row[1] for row in sync_conn.exec_driver_sql("PRAGMA table_info(tickets)").fetchall()]
            if ticket_cols and "workspace_id" not in ticket_cols:
                sync_conn.exec_driver_sql("ALTER TABLE tickets ADD COLUMN workspace_id INTEGER DEFAULT 1")
            
            kc_cols = [row[1] for row in sync_conn.exec_driver_sql("PRAGMA table_info(knowledge_chunks)").fetchall()]
            if kc_cols:
                if "workspace_id" not in kc_cols:
                    sync_conn.exec_driver_sql("ALTER TABLE knowledge_chunks ADD COLUMN workspace_id INTEGER DEFAULT 1")
                if "document_id" not in kc_cols:
                    sync_conn.exec_driver_sql("ALTER TABLE knowledge_chunks ADD COLUMN document_id INTEGER")
                if "chunk_index" not in kc_cols:
                    sync_conn.exec_driver_sql("ALTER TABLE knowledge_chunks ADD COLUMN chunk_index INTEGER DEFAULT 0")
                if "page_number" not in kc_cols:
                    sync_conn.exec_driver_sql("ALTER TABLE knowledge_chunks ADD COLUMN page_number INTEGER DEFAULT 1")
        except Exception as mig_err:
            logger.warning(f"SQLite auto-migration notice: {mig_err}")

    # 1. Synchronize schema, falling back to SQLite if PostgreSQL fails
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            if "sqlite" in engine.url.drivername:
                await conn.run_sync(_migrate_sqlite_columns)
        logger.info(f"Database schema synchronized successfully on {engine.url.drivername}.")
    except Exception as e:
        logger.warning(
            f"Primary database connection failed ({e}). "
            f"Falling back to local async SQLite: {settings.FALLBACK_SQLITE_URL}"
        )
        engine, async_session_factory = create_engine_and_factory(settings.FALLBACK_SQLITE_URL)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            await conn.run_sync(_migrate_sqlite_columns)
        logger.info("Database schema synchronized on fallback SQLite engine.")

    # 2. Seed initial data
    try:
        async with async_session_factory() as session:
            # 2.1 Seed initial Workspaces if empty
            ws_result = await session.execute(select(Workspace).limit(1))
            existing_ws = ws_result.scalars().first()
            if not existing_ws:
                logger.info("Seeding initial workspaces...")
                sample_workspaces = [
                    Workspace(
                        slug="default",
                        name="SmartDesk Cloud Support",
                        industry="IT & SaaS",
                        persona_name="SmartDesk Assistant",
                        tone_of_voice="Chuyên nghiệp, ngắn gọn, thân thiện và chính xác về mặt kỹ thuật.",
                        business_rules="Hỗ trợ xử lý sự cố tài khoản, phân quyền, tích hợp API, thanh toán định kỳ. Luôn bảo vệ an toàn thông tin khách hàng."
                    ),
                    Workspace(
                        slug="smilecare",
                        name="Nha Khoa Thẩm Mỹ SmileCare",
                        industry="Y tế & Nha khoa",
                        persona_name="Bác sĩ SmileCare Bot",
                        tone_of_voice="Ân cần, chu đáo, đồng cảm, chuyên môn y khoa cao nhưng dễ hiểu.",
                        business_rules="Tư vấn niềng răng, bọc sứ, tẩy trắng, cấy ghép Implant. Báo giá dịch vụ minh bạch. Không đưa ra chỉ định thuốc kháng sinh khi chưa có đơn khám."
                    ),
                    Workspace(
                        slug="techstore",
                        name="Hệ Thống Điện Máy TechStore",
                        industry="Bán lẻ thiết bị công nghệ",
                        persona_name="TechStore Advisor",
                        tone_of_voice="Năng động, nhiệt tình, rõ ràng về thông số kỹ thuật và chính sách.",
                        business_rules="Tư vấn điện thoại, laptop, phụ kiện. Hướng dẫn đổi trả 1 đổi 1 trong 30 ngày nếu lỗi kỹ thuật. Quy định trừ phí phụ kiện nếu mất hộp."
                    ),
                ]
                for ws in sample_workspaces:
                    session.add(ws)
                await session.commit()
                logger.info(f"Successfully seeded {len(sample_workspaces)} workspaces.")

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

            # 2.4 Seed sample documents for Workspace 2 (SmileCare) & Workspace 3 (TechStore)
            from app.models.document import Document
            from pathlib import Path
            from app.services.document_service import document_service

            for ws_id, fname, rel_path in [
                (2, "nha_khoa_smilecare_bang_gia_dich_vu.txt", "sample_documents/nha_khoa_smilecare_bang_gia_dich_vu.txt"),
                (3, "dien_may_techstore_chinh_sach_doi_tra.txt", "sample_documents/dien_may_techstore_chinh_sach_doi_tra.txt"),
            ]:
                doc_res = await session.execute(select(Document).where(Document.workspace_id == ws_id))
                doc_obj = doc_res.scalars().first()
                if doc_obj:
                    if doc_obj.status != "published":
                        doc_obj.status = "published"
                        await session.commit()
                        logger.info(f"Published existing document for workspace {ws_id}.")
                else:
                    doc_path = Path("backend/data") / rel_path
                    if not doc_path.exists():
                        doc_path = Path("data") / rel_path
                    if doc_path.exists():
                        try:
                            content_bytes = doc_path.read_bytes()
                            new_doc = await document_service.process_and_store_document(
                                workspace_id=ws_id,
                                filename=fname,
                                file_bytes=content_bytes,
                                session=session
                            )
                            new_doc.status = "published"
                            await session.commit()
                            logger.info(f"Successfully seeded and published workspace {ws_id} sample document.")
                        except Exception as e:
                            logger.warning(f"Error seeding workspace {ws_id} document: {e}")
    except Exception as e:
        logger.error(f"Error during database initialization: {e}", exc_info=True)
        # For non-fatal database initialization failure, allow fallback
