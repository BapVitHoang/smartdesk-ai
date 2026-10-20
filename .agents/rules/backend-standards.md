# Backend Development Rules & Standards

## 1. Stack & Architecture
- Framework: **FastAPI (Python 3.11+)** asynchronous ASGI service.
- Database: **SQLAlchemy 2.0 (Async)** with PostgreSQL 16 + `pgvector` or SQLite (`aiosqlite`) fallback.
- AI Providers: Google Gemini (`gemini-3.5-flash-lite` primary, `gemini-2.5-flash-lite` fallback, `gemini-embedding-001` embeddings) and local Ollama (`qwen2.5:3b` + `nomic-embed-text`).
- Code layout under `backend/app/`:
  - `core/`: Configuration (`config.py`), externalized prompts (`prompts.py`), security guardrails (`security.py`), custom exception handlers (`exceptions.py`).
  - `db/`: Async session factory (`get_db`, `get_session_factory`) and base model.
  - `models/`: ORM entities (`Ticket`, `FAQItem`, `KnowledgeChunk`, `Workspace`, `Document`, `VerificationReport`, `VerificationItem`).
  - `schemas/`: Pydantic v2 schemas for requests, responses, and error objects.
  - `services/`: Business logic (`llm_service`, `embedding_service`, `rag_service`, `fallback_service`, `ticket_service`, `document_service`, `verification_service`, `agent_tools`).
  - `api/v1/endpoints/`: Route handlers (`chat`, `tickets`, `agent`, `knowledge`, `workspaces`, `documents`, `health`).

## 2. Async I/O Enforcement
- NEVER use blocking synchronous calls (e.g. `requests.get()`, `time.sleep()`).
- Use `httpx.AsyncClient` for external HTTP calls and `asyncio.sleep()`.
- Inject database sessions using `session: AsyncSession = Depends(get_db)`.

## 3. Strict Typing, Categories & SLA Validation
- Explicit type annotations on all function signatures (`typing.Optional`, `typing.List`, `typing.Dict`).
- All incoming payloads and outgoing responses MUST adhere to Pydantic v2 schemas defined in `docs/API_CONTRACT.md`.
- Canonical Ticket Categories: `"Authentication"`, `"Billing"`, `"Bug Report"`, `"Feature Request"`, `"General"` (with `"Technical Bug"` accepted as an alias for `"Bug Report"`).
- Canonical SLA Hours: `Urgent` = 2h, `High` = 4h, `Medium` = 8h, `Low` = 24h.

## 4. Error Handling & Status Codes
- All errors follow standardized JSON structure (`detail`, `error_code`, `status_code`, `details`).
- Injections or invalid input: HTTP 400 with `error_code: "PROMPT_SECURITY_VIOLATION"` or `"VALIDATION_ERROR"`.
- Resource not found: HTTP 404 with structured error schema (`TICKET_NOT_FOUND`, `RESOURCE_NOT_FOUND`).
- Gemini failure or timeout: DO NOT return HTTP 500 to the client; gracefully degrade to BM25 fallback with HTTP 200 and `"is_fallback": true`.

## 5. Module Ownership & Pre-Commit Check
- Respect module ownership in `docs/ARCHITECTURE.md`. Do not modify shared files (`api.py`, `config.py`, `main.py`) without Integration Owner approval.
- Always run `pytest backend/tests/ -v` before committing.
