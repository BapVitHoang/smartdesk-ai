# Backend Development Rules & Standards

## 1. Stack & Architecture
- Framework: **FastAPI (Python 3.11+)** asynchronous ASGI service.
- Database: **SQLAlchemy 2.0 (Async)** with PostgreSQL 16 + `pgvector` or SQLite (`aiosqlite`) fallback.
- Code layout under `backend/app/`:
  - `core/`: Configuration, security guardrails, custom exception handlers.
  - `db/`: Async session factory (`get_db`) and base model.
  - `models/`: ORM entities (`Ticket`, `FAQItem`, `KnowledgeChunk`).
  - `schemas/`: Pydantic v2 schemas for requests, responses, and error objects.
  - `services/`: Business logic (`llm_service`, `rag_service`, `fallback_service`, `ticket_service`).
  - `api/v1/endpoints/`: Route handlers (`chat`, `tickets`, `agent`, `knowledge`, `health`).

## 2. Async I/O Enforcement
- NEVER use blocking synchronous calls (e.g. `requests.get()`, `time.sleep()`).
- Use `httpx.AsyncClient` for external HTTP calls and `asyncio.sleep()`.
- Inject database sessions using `session: AsyncSession = Depends(get_db)`.

## 3. Strict Typing & Pydantic Validation
- Explicit type annotations on all function signatures (`typing.Optional`, `typing.List`, `typing.Dict`).
- All incoming payloads and outgoing responses MUST adhere to Pydantic v2 schemas defined in `API_CONTRACT.md`.

## 4. Error Handling & Status Codes
- Injections or invalid input: HTTP 400 with `error_code: "PROMPT_SECURITY_VIOLATION"` or `"VALIDATION_ERROR"`.
- Resource not found: HTTP 404 with structured error schema.
- Gemini failure or timeout: DO NOT return HTTP 500 to the client; gracefully degrade to BM25 fallback with HTTP 200 and `"is_fallback": true`.
