"""Utility script to export training dataset from SmartDesk AI FAQ items and tickets into JSONL format for Fine-Tuning (Alpaca / ShareGPT format).

Usage:
    python backend/scripts/export_finetune_dataset.py --output backend/data/finetune_alpaca.jsonl
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from sqlalchemy import select
from app.core.config import BACKEND_DIR
from app.db import session as db_session
from app.models.knowledge import FAQItem
from app.models.ticket import Ticket


async def export_dataset(output_path: str) -> None:
    print(f"Exporting fine-tuning dataset to: {output_path}")
    await db_session.init_db()

    dataset = []

    async with db_session.async_session_factory() as session:
        # 1. Export from FAQ items
        faqs_res = await session.execute(select(FAQItem))
        faqs = faqs_res.scalars().all()

        for faq in faqs:
            # Entry: Customer question -> Ground truth support answer
            entry = {
                "instruction": f"Bạn là Trợ lý SmartDesk AI hỗ trợ danh mục {faq.category}. Hãy trả lời câu hỏi của khách hàng một cách ngắn gọn, chính xác.",
                "input": faq.title,
                "output": f"{faq.content} [Doc #{faq.doc_id}: {faq.title}]"
            }
            dataset.append(entry)

        # 2. Export from resolved tickets with drafts
        tickets_res = await session.execute(select(Ticket))
        tickets = tickets_res.scalars().all()

        for t in tickets:
            if t.ai_draft_reply and len(t.ai_draft_reply.strip()) > 20:
                entry = {
                    "instruction": f"Bạn là Trợ lý SmartDesk AI. Hãy viết phản hồi chuyên nghiệp giải quyết khiếu nại/yêu cầu sau của khách hàng (Độ khẩn cấp: {t.priority}).",
                    "input": f"Tiêu đề: {t.subject}\nNội dung khiếu nại: {t.description}",
                    "output": t.ai_draft_reply.strip()
                }
                dataset.append(entry)

    out_file = Path(output_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)

    with open(out_file, "w", encoding="utf-8") as f:
        for item in dataset:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    print(f"Successfully exported {len(dataset)} training examples to {out_file.resolve()}.")


if __name__ == "__main__":
    default_out = (BACKEND_DIR / "data" / "finetune_alpaca.jsonl").as_posix()
    parser = argparse.ArgumentParser(description="Export SmartDesk AI Fine-tuning Dataset")
    parser.add_argument("--output", default=default_out, help="Output JSONL path")
    args = parser.parse_args()
    asyncio.run(export_dataset(args.output))
