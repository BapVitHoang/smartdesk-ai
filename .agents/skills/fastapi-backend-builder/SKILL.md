---
name: fastapi-backend-builder
description: >-
  Build, scaffold, and test the FastAPI asynchronous backend for SmartDesk AI.
  Use when implementing API endpoints (/api/v1/chat, /api/v1/tickets, /api/v1/agent, /api/v1/health),
  setting up Google Gemini 1.5 Flash RAG pipeline, configuring PostgreSQL pgvector,
  or implementing the non-AI BM25 fallback mechanism.
---

# FastAPI Backend Builder Skill for SmartDesk AI

This skill guides the AI assistant through developing, maintaining, and testing the production-ready FastAPI backend for **SmartDesk AI - Intelligent Customer Support & Knowledge Synthesizer**.

---

## 1. Quick Verification & Prerequisites

Before modifying or generating code:
1. Ensure Python 3.11+ is installed.
2. Check environment variables (`GEMINI_API_KEY`, `DATABASE_URL`).
3. Verify that the file structure matches the modular layout described in `AGENTS.md`.

---

## 2. Standard Implementation Workflow

### Step 1: Core Configuration & Database Setup
- Path: `backend/app/core/config.py`
- Use `pydantic_settings.BaseSettings` with `.env` reading.
- Key settings:
  ```python
  GEMINI_API_KEY: str = ""
  DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/smartdesk"
  FALLBACK_SQLITE_URL: str = "sqlite+aiosqlite:///./test.db"
  LLM_TIMEOUT_SECONDS: float = 4.0
  CORS_ORIGINS: list[str] = ["http://localhost:3000"]
  ```

### Step 2: Database Models & Schemas
- Model `Ticket`:
  - `id`: Integer primary key
  - `ticket_code`: `#TICK-XXXX`
  - `customer_name`, `customer_email`: String
  - `category`, `priority`: Enum or String
  - `subject`, `description`: Text
  - `status`: `open` | `in_progress` | `resolved`
  - `ai_tags`: JSON array of strings
  - `ai_draft_reply`: Text nullable
- Model `FAQItem` / `KnowledgeChunk`:
  - `id`: Integer
  - `title`, `content`, `category`, `source_url`: Text
  - `embedding`: Vector(768) (pgvector or serialized array fallback)

### Step 3: Implement Pure Services (`app/services/`)
1. **`llm_service.py`**:
   - Wrap Google Gemini 1.5 Flash using `google-genai` or `google-generativeai`.
   - Measure real-time latency with `time.perf_counter()`.
   - Strictly wrap calls in `asyncio.wait_for(..., timeout=config.LLM_TIMEOUT_SECONDS)`.
2. **`fallback_service.py`**:
   - Pure Python non-AI deterministic FAQ matcher.
   - Load `backend/data/seed_faq.json`.
   - Compute matching score using token overlap / BM25 / Jaccard similarity.
   - Return top match or fallback template with zero LLM dependency.
3. **`rag_service.py`**:
   - Embed user query with `text-embedding-004`.
   - Query similarity against `KnowledgeChunk`.
   - Build grounded prompt with citations: `[Doc #X: title]`.
   - If error or timeout occurs, smoothly invoke `fallback_service.py`.
4. **`ticket_service.py`**:
   - Handle ticket creation with auto-generated `#TICK-XXXX`.
   - Async background task to analyze ticket category/priority and write `ai_draft_reply`.

### Step 4: Router Endpoints (`app/api/v1/endpoints/`)
- `POST /api/v1/chat`: Returns response, citations, latency_ms, is_fallback.
- `POST /api/v1/tickets`: Submit customer ticket with validation.
- `GET /api/v1/tickets`: Query/filter tickets for Agent Triage Dashboard.
- `PATCH /api/v1/tickets/{id}`: Agent edit draft or status.
- `POST /api/v1/agent/tickets/{id}/generate-draft`: AI Copilot regeneration.
- `GET /api/v1/health`: Basic readiness & DB ping.
- `GET /api/v1/health/smoke-test`: Executes live LLM call and returns latency report matching `scripts/smoke_test.py`.

---

## 3. Execution & Testing Commands

To run and verify the backend:
```bash
# Install dependencies
pip install -r backend/requirements.txt

# Run server in reload mode
cd backend && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Run smoke test endpoint
curl http://localhost:8000/api/v1/health/smoke-test

# Run automated tests
pytest tests/ -v
```

---

## 4. Troubleshooting & Fallback Matrix
- **Problem: Gemini API Rate Limit (HTTP 429) or Outage**:
  - `rag_service.py` catches `Exception` -> calls `fallback_service.match_faq()` -> response has `"is_fallback": true`.
- **Problem: PostgreSQL pgvector not available locally**:
  - `db/session.py` catches connection error or uses SQLite in-memory cosine fallback for vector similarity during development.
