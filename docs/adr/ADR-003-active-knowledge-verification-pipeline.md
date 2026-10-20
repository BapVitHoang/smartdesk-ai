# ADR-003: Three-Stage Active Knowledge Verification Pipeline Before RAG Publication

- **Status:** Accepted
- **Date:** 2026-10-20
- **Deciders:** SmartDesk AI Architecture Team (`Owner 1: AI & RAG`)

## 1. Context
In enterprise customer support, directly indexing newly uploaded `.pdf`, `.txt`, or `.md` files into production RAG is dangerous: poorly formatted documents, OCR artifacts, or contradictory pricing rules can cause the chatbot to give inaccurate answers to customers.

## 2. Decision
We introduced a mandatory **Publication Gate** (`status: "pending" -> "verified" -> "published"`) backed by a **3-Stage Active Verification Engine** (`backend/app/services/verification_service.py`):
1. **Stage 1 — Synthetic Q&A Generation:** Automatically extracts 3 representative `(question, ground_truth)` pairs from the uploaded document's chunks.
2. **Stage 2 — Parallel RAG Self-Test (`asyncio.gather`):** Executes all synthetic questions concurrently against the workspace's retrieval pipeline to capture actual `rag_answer` outputs in < 3 seconds.
3. **Stage 3 — AI Judge Faithfulness Scoring:** Evaluates each `(ground_truth, rag_answer)` pair on a `0.0–1.0` scale (`passed` $\ge 0.85$, `warning` $0.60–0.84$, `failed` $< 0.60$) using defensive JSON extraction (`clean_json_response`) and persists a `VerificationReport` for human admin sign-off before `POST /api/v1/documents/{id}/publish`.

## 3. Alternatives Considered
- **Immediate Auto-Publish on Upload:** Rejected because unverified chunks could immediately pollute customer-facing RAG responses.
- **Sequential Verification Execution:** Rejected because running 3 RAG + 3 Judge calls sequentially took 6–9 seconds, exceeding the frontend's default 5-second timeout. Parallelizing with `asyncio.gather()` and setting a 15-second timeout on `/verify` solved this.

## 4. Consequences
- **Positive:** Provides auditable faithfulness metrics per document and guarantees that `rag_service.py` only retrieves chunks from `status == "published"` documents.
- **Negative / Trade-off:** Requires an extra click ("Verify" $\to$ "Publish") in the Knowledge Studio UI before newly uploaded files appear in customer chat.
