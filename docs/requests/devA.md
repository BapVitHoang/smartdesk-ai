# Change Request: REQ-16 AI Multimodal Input & Vision Fallback for Document Upload

**Author / Developer:** Dev A (AI Engine - `@TheOrijinnn`)  
**Date:** 2026-10-23  
**Status:** Pending  
**Target Module / Owner:** Dev B (Platform & Document Ingestion - `backend/app/services/document_service.py`) & Integrator (`backend/app/core/config.py`)

---

## 1. Reason for Change & Requirement Traceability
- **Requirement Traceability:** `REQ-16` / Capability D (Multimodal Input) under `CRIT-03` (25% weight).
  - *Quote from Project Specification (`docs/audit/00-checklist.md:28`):*
    > *"Images, PDFs or voice are processed by AI (e.g., receipt reading, document extraction, speech-to-text), and the result is stored and used by the app."*
- **Audit Defect Identified (`docs/audit/01-gap-analysis.md:52`):**
  - Current PDF ingestion in `backend/app/services/document_service.py#L39-L64` relies strictly on `pypdf.PdfReader` text extraction.
  - This is a non-AI deterministic parser that extracts existing ASCII/Unicode glyphs from digital text layers.
  - When a user uploads a scanned document, receipt image, or image-only PDF, `document_service.py#L61-L62` currently rejects the upload with an error:
    `"Tệp PDF scan dạng hình ảnh không chứa text layer. Vui lòng sử dụng tệp PDF chứa văn bản hoặc tệp Markdown / Text."`
  - Neither scanned PDFs nor images are processed by AI, leaving Capability D only partially satisfied.

---

## 2. Proposed Architectural Solution

Dev A proposes adding an AI Vision fallback mechanism directly into `document_service.py`:
1. When `pypdf.PdfReader` extracts text with total length `< 50` characters (indicating a scanned or image-based PDF), or when the uploaded file is an image (`image/png`, `image/jpeg`), trigger the AI Vision pipeline.
2. The AI Vision pipeline will call Google Gemini 3.5 Flash Lite multimodal capabilities (`client.models.generate_content`) passing the raw file bytes as `types.Part.from_bytes(data=content, mime_type=mime_type)`.
3. The extracted text is then chunked, embedded, and stored in `KnowledgeChunk` exactly like regular text documents.

### Proposed Code Diff for `backend/app/services/document_service.py` (Dev B file):

```python
# In DocumentService._extract_text_from_pdf()
async def _extract_text_from_pdf(self, content: bytes) -> str:
    # 1. Attempt non-AI fast extraction via pypdf
    extracted_text = ""
    try:
        reader = pypdf.PdfReader(io.BytesIO(content))
        for page_idx, page in enumerate(reader.pages):
            txt = page.extract_text() or ""
            if txt.strip():
                extracted_text += f"\n--- Trang {page_idx + 1} ---\n" + txt.strip()
    except Exception as e:
        logger.warning(f"pypdf extraction failed: {e}")

    # 2. AI Multimodal Fallback if text layer is empty or scanned (REQ-16)
    if len(extracted_text.strip()) < 50:
        logger.info("PDF has empty text layer or is a scanned image. Invoking Gemini 3.5 Multimodal OCR...")
        from app.services.llm_service import llm_service
        from google.genai import types

        if llm_service._client and llm_service.is_available():
            ocr_prompt = (
                "Bạn là trợ lý OCR chuyên nghiệp. Hãy trích xuất và số hóa toàn bộ nội dung văn bản, "
                "bảng biểu, chính sách trong tài liệu này một cách chính xác dưới định dạng Markdown."
            )
            part = types.Part.from_bytes(data=content, mime_type="application/pdf")
            response = await asyncio.to_thread(
                llm_service._client.models.generate_content,
                model=llm_service.model_name,
                contents=[part, ocr_prompt],
            )
            extracted_text = (response.text or "").strip()

    if not extracted_text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Không thể trích xuất văn bản từ tệp PDF (cả qua Text Layer lẫn AI Multimodal OCR)."
        )

    return extracted_text
```

---

## 3. Impact Analysis & Module Boundaries
- **Ownership Boundary:** `document_service.py` belongs to Dev B. Dev A does NOT modify it directly.
- **Backward Compatibility:** 100% backward compatible. Standard text PDFs will continue to be processed fast (< 50ms) by `pypdf`, while scanned PDFs and images will gracefully activate Gemini Vision instead of throwing an HTTP 400 error.
- **Dependencies:** Uses already installed `google-genai` SDK and existing `GEMINI_API_KEY`. No new third-party dependencies required.

---

## 4. Integration Review & Sign-Off
- [ ] Reviewed by Dev B (`@BapVitHoang`)
- [ ] Reviewed by Lead / Integration Owner
- [ ] Verified with `python -m pytest backend/tests/test_workspace_and_verification.py -v`

---

## 5. Post-Merge Integration Requests (Prompt M / S-A)

REQ-AI-01 | docs/spec/CONTRACTS.md:55 | In CONTRACTS.md §2, add "config_error" to status Literal["success", "fallback", "refused", "config_error"] (called in rag_service.py:448 and ticket_copilot_service.py:186 on LLMConfigException to prevent false HTTP 429 cooldowns) | integrator | PENDING

