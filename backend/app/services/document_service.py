"""Document ingestion, recursive chunking, text extraction, and cascade deletion."""

import io
import logging
from typing import Any, Dict, List, Tuple
from pathlib import Path
import pypdf
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document
from app.models.knowledge import KnowledgeChunk
from app.models.verification import VerificationReport, VerificationItem
from app.services.embedding_service import embedding_service

logger = logging.getLogger("smartdesk.document")

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
MAX_PAGES = 15
MAX_CHUNKS = 40


class DocumentService:
    """Service handling file extraction, text chunking, and database persistence."""

    @staticmethod
    def extract_text_from_file(file_bytes: bytes, filename: str) -> List[Tuple[str, int]]:
        """
        Extracts text content per page from supported file types (.pdf, .txt, .md).
        
        Returns:
            List[Tuple[str, int]]: List of (page_text, page_number) pairs (1-indexed).
        """
        if len(file_bytes) > MAX_FILE_SIZE:
            raise ValueError(f"Dung lượng tệp vượt quá giới hạn cho phép (Tối đa {MAX_FILE_SIZE // (1024 * 1024)}MB).")

        ext = Path(filename).suffix.lower()

        if ext == ".pdf":
            try:
                reader = pypdf.PdfReader(io.BytesIO(file_bytes))
            except Exception as e:
                raise ValueError(f"Không thể đọc cấu trúc tệp PDF: {e}")

            num_pages = len(reader.pages)
            if num_pages > MAX_PAGES:
                raise ValueError(f"Tệp PDF vượt quá giới hạn số trang cho phép (Tối đa {MAX_PAGES} trang, tệp có {num_pages} trang).")

            pages: List[Tuple[str, int]] = []
            has_content = False
            for page_idx, page in enumerate(reader.pages):
                try:
                    text = page.extract_text() or ""
                except Exception:
                    text = ""
                clean_text = text.strip()
                if clean_text:
                    has_content = True
                pages.append((clean_text, page_idx + 1))

            if not has_content:
                raise ValueError("Tệp PDF scan dạng hình ảnh không chứa text layer có thể bóc tách.")

            return pages

        elif ext in [".txt", ".md"]:
            # Try multiple encodings
            text = None
            for encoding in ["utf-8", "utf-8-sig", "latin-1"]:
                try:
                    text = file_bytes.decode(encoding)
                    break
                except UnicodeDecodeError:
                    continue

            if text is None:
                raise ValueError("Không thể giải mã nội dung văn bản. Vui lòng đảm bảo tệp định dạng UTF-8.")

            clean_text = text.strip()
            if not clean_text:
                raise ValueError("Nội dung tệp trống.")

            return [(clean_text, 1)]

        else:
            raise ValueError("Định dạng tệp không được hỗ trợ. Vui lòng tải lên tệp .pdf, .txt hoặc .md.")

    @staticmethod
    def recursive_character_splitter(
        text: str,
        page_number: int = 1,
        chunk_size: int = 700,
        chunk_overlap: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Hierarchically splits text using recursive delimiters [\\n\\n, \\n, . , , , space].
        """
        if not text:
            return []

        separators = ["\n\n", "\n", ". ", ", ", " "]

        def _split_text(content: str, seps: List[str]) -> List[str]:
            if len(content) <= chunk_size or not seps:
                return [content] if content.strip() else []

            sep = seps[0]
            remaining_seps = seps[1:]
            splits = content.split(sep)

            pieces: List[str] = []
            for s in splits:
                s_strip = s.strip()
                if not s_strip:
                    continue
                if len(s_strip) > chunk_size:
                    pieces.extend(_split_text(s_strip, remaining_seps))
                else:
                    pieces.append(s_strip)
            return pieces

        raw_pieces = _split_text(text, separators)
        if not raw_pieces:
            return []

        chunks: List[str] = []
        current_chunk = ""

        for piece in raw_pieces:
            if not current_chunk:
                current_chunk = piece
            elif len(current_chunk) + len(piece) + 1 <= chunk_size:
                current_chunk += " " + piece
            else:
                chunks.append(current_chunk)
                # Keep overlap from the end of current_chunk
                overlap_len = min(len(current_chunk), chunk_overlap)
                overlap_text = current_chunk[-overlap_len:].strip()
                current_chunk = (overlap_text + " " + piece).strip()

        if current_chunk and current_chunk not in chunks:
            chunks.append(current_chunk)

        result: List[Dict[str, Any]] = []
        for idx, chunk_str in enumerate(chunks):
            result.append({
                "content": chunk_str,
                "page_number": page_number,
                "chunk_index": idx,
                "token_estimate": max(1, len(chunk_str) // 4)
            })

        return result

    async def process_and_store_document(
        self,
        file_bytes: bytes,
        filename: str,
        workspace_id: int,
        session: AsyncSession
    ) -> Document:
        """
        Full pipeline: text extraction -> recursive chunking -> throttled embedding -> database storage.
        """
        # 1. Text Extraction
        pages = self.extract_text_from_file(file_bytes, filename)
        ext = Path(filename).suffix.lower()

        # 2. Chunking
        all_chunks: List[Dict[str, Any]] = []
        full_text_parts: List[str] = []

        chunk_counter = 0
        for page_text, page_num in pages:
            if not page_text:
                continue
            full_text_parts.append(page_text)
            page_chunks = self.recursive_character_splitter(
                page_text, page_number=page_num, chunk_size=700, chunk_overlap=100
            )
            for chk in page_chunks:
                chk["chunk_index"] = chunk_counter
                all_chunks.append(chk)
                chunk_counter += 1
                if chunk_counter >= MAX_CHUNKS:
                    break
            if chunk_counter >= MAX_CHUNKS:
                logger.info(f"Reached MAX_CHUNKS cap ({MAX_CHUNKS}) for document {filename}.")
                break

        if not all_chunks:
            raise ValueError("Không thể tạo các đoạn kiến thức (chunks) từ tệp này.")

        # 3. Create Document Record
        doc = Document(
            workspace_id=workspace_id,
            filename=filename,
            file_type=ext.replace(".", ""),
            file_size=len(file_bytes),
            status="pending",
            chunk_count=len(all_chunks),
            raw_text="\n\n".join(full_text_parts)
        )
        session.add(doc)
        await session.flush()  # Flush to get doc.id

        # 4. Compute embeddings in throttled batches
        chunk_texts = [c["content"] for c in all_chunks]
        embeddings = await embedding_service.get_text_embeddings_batch(chunk_texts, batch_size=5)

        # 5. Store Knowledge Chunks
        for idx, (chunk_data, emb) in enumerate(zip(all_chunks, embeddings)):
            kc = KnowledgeChunk(
                chunk_id=f"doc-{doc.id}-chk-{idx + 1}",
                parent_doc_id=f"doc-{doc.id}",
                workspace_id=workspace_id,
                document_id=doc.id,
                chunk_index=chunk_data["chunk_index"],
                page_number=chunk_data["page_number"],
                title=f"{filename} - Trang {chunk_data['page_number']} (Mục {idx + 1})",
                content=chunk_data["content"],
                source_url=f"/documents/{doc.id}/page/{chunk_data['page_number']}",
                embedding=emb
            )
            session.add(kc)

        await session.commit()
        await session.refresh(doc)
        logger.info(f"Stored document ID={doc.id} ({filename}) with {len(all_chunks)} chunks.")
        return doc

    async def delete_document_safely(self, document_id: int, session: AsyncSession) -> bool:
        """
        Safely deletes document and cascades deletion of chunks, reports, and report items
        to prevent orphan records on SQLite.
        """
        # Find document
        doc_result = await session.execute(select(Document).where(Document.id == document_id))
        doc = doc_result.scalar_one_or_none()
        if not doc:
            return False

        # Find verification reports to delete their items
        report_result = await session.execute(
            select(VerificationReport).where(VerificationReport.document_id == document_id)
        )
        reports = report_result.scalars().all()
        for r in reports:
            await session.execute(
                delete(VerificationItem).where(VerificationItem.report_id == r.id)
            )
            await session.delete(r)

        # Delete knowledge chunks
        await session.execute(
            delete(KnowledgeChunk).where(KnowledgeChunk.document_id == document_id)
        )

        # Delete document
        await session.delete(doc)
        await session.commit()
        logger.info(f"Safely deleted document {document_id} and all cascaded chunks/reports.")
        return True


document_service = DocumentService()
