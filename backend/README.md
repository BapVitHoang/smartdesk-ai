# SmartDesk AI - Backend Service

> **Service:** Asynchronous AI Customer Support & Knowledge Synthesizer  
> **Framework:** FastAPI (Python 3.11+)  
> **Architecture:** Clean Layered Architecture (Async 100%, Pydantic v2, Circuit Breaker RAG)

---

## 1. Overview & Architecture

The **SmartDesk AI** backend provides high-performance, resilient customer support automation combining:
- **Retrieval-Augmented Generation (RAG):** Grounded answering powered by Google Gemini 1.5 Flash with strict source citation badges.
- **Latency Budget & Circuit Breaker (4.0s max):** Automatically falls back to deterministic BM25 / Keyword matching on curated FAQ knowledge with `"is_fallback": true` and prompt escalation.
- **Agent Copilot & Ticket Triage:** Auto-assigns `#TICK-XXXX` codes, tags categories/priorities, calculates SLA response times, and drafts personalized resolution responses.
- **Async Database Engine:** Dual support for PostgreSQL (with `pgvector`) and SQLite Async (`aiosqlite`) for zero-friction local development.

---

## 2. Directory Structure

```text
backend/
├── app/
│   ├── api/v1/endpoints/   # REST Endpoints (chat, tickets, agent, health)
│   ├── core/               # App configuration, security guardrails, custom exceptions
│   ├── db/                 # Async database session & schema initialization
│   ├── models/             # SQLAlchemy 2.0 ORM models (Ticket, FAQItem, KnowledgeChunk)
│   ├── schemas/            # Pydantic v2 Request/Response contracts
│   ├── services/           # Business logic (LLM wrapper, BM25 fallback, RAG, Ticket Copilot)
│   └── main.py             # FastAPI ASGI entrypoint, CORS, exception handlers
├── data/
│   └── seed_faq.json       # 12 curated support FAQ articles for fallback & DB seeding
├── tests/
│   └── test_api.py         # Automated integration tests (pytest + httpx)
├── .env.example            # Environment configuration template
├── Dockerfile              # Production container build
└── requirements.txt        # Python dependencies
```

---

## 3. Quickstart & Installation

### Step 1: Install Dependencies
```bash
cd backend
pip install -r requirements.txt
```

### Step 2: Configure Environment
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Key configuration settings in `.env`:
- `GEMINI_API_KEY`: Your Google Gemini API Key from [Google AI Studio](https://aistudio.google.com/). *(Optional: If omitted, the deterministic fallback engine activates automatically).*
- `DATABASE_URL`: Defaults to `sqlite+aiosqlite:///./smartdesk.db` for instant local execution.
- `LLM_TIMEOUT_SECONDS`: `4.0` (Hard ceiling for external AI calls).

### Step 3: Run the Development Server
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
The server will start at `http://localhost:8000`. Interactive OpenAPI documentation is available at:
- **Swagger UI:** `http://localhost:8000/docs`
- **ReDoc:** `http://localhost:8000/redoc`

---

## 4. API Endpoints Summary

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/v1/chat` | Customer RAG inquiry with citation badges & circuit breaker |
| `POST` | `/api/v1/tickets` | Submit customer ticket with auto `#TICK-XXXX`, AI tags & draft |
| `GET` | `/api/v1/tickets` | List tickets with filters (`status`, `category`, `priority`, `search`) |
| `GET` | `/api/v1/tickets/{id}` | Get ticket details by ID or code |
| `PATCH` | `/api/v1/tickets/{id}` | Update ticket status or customize AI draft reply |
| `POST` | `/api/v1/agent/tickets/{id}/generate-draft` | AI Copilot regenerate draft resolution |
| `GET` | `/api/v1/health` | Service readiness probe & database ping |
| `GET` | `/api/v1/health/smoke-test` | Live Gemini LLM round-trip benchmark & latency report |

---

## 5. Running Automated Tests

Run the comprehensive async test suite with `pytest`:
```bash
pytest tests/ -v
```
All tests execute against an isolated async SQLite database and verify:
- Health & Smoke-test benchmarks.
- RAG chat and Fallback Circuit Breaker activation.
- Prompt injection security defense.
- Ticket CRUD, auto-tagging, and Copilot draft reply generation.
