"""Database seed coordinator package."""

import json
import logging
from pathlib import Path
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import BACKEND_DIR, settings
from app.models.workspace import Workspace
from app.models.knowledge import FAQItem
from app.models.document import Document
from app.services.document_service import document_service

from app.db.seed.seed_users import seed_users
from app.db.seed.seed_tickets import seed_tickets
from app.db.seed.seed_ai_usage import seed_ai_usage

logger = logging.getLogger("smartdesk.seed")


async def seed_workspaces(session: AsyncSession) -> None:
    """Seeds default and tenant workspaces."""
    ws_result = await session.execute(select(Workspace).limit(1))
    if ws_result.scalars().first():
        return

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


async def seed_faq(session: AsyncSession) -> None:
    """Seeds default IT FAQ knowledge items from seed_faq.json."""
    result = await session.execute(select(FAQItem).limit(1))
    if result.scalars().first():
        return

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


async def seed_sample_documents(session: AsyncSession) -> None:
    """Seeds sample documents for Workspace 2 and Workspace 3."""
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
        else:
            doc_path = BACKEND_DIR / "data" / rel_path
            if not doc_path.exists():
                doc_path = Path("backend/data") / rel_path
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
                    logger.info(f"Seeded and published workspace {ws_id} document {fname}.")
                except Exception as e:
                    logger.warning(f"Error seeding workspace {ws_id} document: {e}")


async def seed_all(session: AsyncSession) -> None:
    """Executes all seed modules in dependency order."""
    await seed_workspaces(session)
    await seed_users(session)
    await seed_faq(session)
    await seed_tickets(session)
    await seed_ai_usage(session)
    await seed_sample_documents(session)


__all__ = [
    "seed_all",
    "seed_users",
    "seed_tickets",
    "seed_ai_usage",
    "seed_workspaces",
    "seed_faq",
    "seed_sample_documents",
]
