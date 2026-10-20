# SmartDesk AI - Rules & Guidelines for AI Assistant

This file outlines the foundational technical rules, architecture constraints, module ownership boundaries, and coding standards that every developer and AI assistant must strictly follow when working on **SmartDesk AI**.

---

## 1. Project Context & Mandatory Document Index

### 1.1 Core Architecture
- **System Name:** SmartDesk AI (Intelligent Customer Support & Knowledge Synthesizer).
- **Frontend:** React 19 + Vite 6 + Tailwind CSS v4 + TypeScript + Lucide Icons + Motion (Single Page Application, NOT Next.js).
- **Backend:** FastAPI (Python 3.11+) asynchronous ASGI service.
- **Database:** PostgreSQL 16 with `pgvector` (Fallback: Async SQLite `aiosqlite` with in-Python cosine similarity for local development/testing).
- **Primary Cloud LLM:** Google Gemini (`gemini-3.5-flash-lite` primary, automatic fallback to `gemini-2.5-flash-lite`; replacing retired `gemini-1.5-flash`), embeddings via `gemini-embedding-001` (replacing retired `text-embedding-004`).
- **Local AI Provider (Dual-Mode):** Ollama (`qwen2.5:3b` + `nomic-embed-text`) via `AI_PROVIDER=ollama`.
- **Deterministic Non-AI Fallback:** Pure-Python Okapi BM25 FAQ matcher on curated dataset (`backend/data/seed_faq.json`) + deterministic SHA-256 768-dim unit pseudo-embeddings when offline or rate-limited.

### 1.2 Mandatory Document Reference Index
Before implementing any task, the AI assistant MUST consult the following canonical documents:
1. **System Architecture & Module Ownership:** [`docs/ARCHITECTURE.md`](./docs/ARCHITECTURE.md) - Folder ownership, shared files policy, and extension points.
2. **API Specifications & Schemas:** [`docs/API_CONTRACT.md`](./docs/API_CONTRACT.md) - Full request/response schemas, error codes, and HTTP status contracts.
3. **UI/UX & Design Tokens:** [`docs/DESIGN.md`](./docs/DESIGN.md) - Brand colors, typography hierarchy, UI state handling, and component specs.
4. **Acceptance Test Matrix:** [`docs/TEST_ACCEPTANCE.md`](./docs/TEST_ACCEPTANCE.md) - Core acceptance test scenarios and automated verification instructions.
5. **Project Proposal & Traceability:** [`docs/PROPOSAL.md`](./docs/PROPOSAL.md) - User stories (`US-01..US-12`) and Requirement Traceability Matrix.
6. **AI Usage & Verification Log:** [`AI_USAGE.md`](./AI_USAGE.md) & [`docs/adr/`](./docs/adr/) - AI collaboration log and Architecture Decision Records (`ADR-001..004`).
7. **General Overview & Startup:** [`README.md`](./README.md) - Quickstart guide and Windows batch script definitions (`scripts/start.bat`, `scripts/start_all.bat`, `scripts/start_backend.bat`, `scripts/install.bat`).

---

## 2. Strict Frontend Architecture Rules

### 2.1 Code Structure & Organization
All frontend code is structured under `frontend/src/`:
```text
frontend/src/
├── components/                  # Core views & shared navigation
│   ├── Header.tsx               # Top navigation, active tab switcher, demo state switcher
│   ├── ChatView.tsx             # Customer RAG chat, citation badges, workspace selector
│   ├── TicketFormView.tsx       # Ticket submission form, SLA preview, live validation
│   ├── AgentDashboardView.tsx   # Agent triage table, filtering, AI copilot draft review
│   ├── KnowledgeManagerView.tsx # Workspace persona config, doc upload, AI verification studio
│   └── Footer.tsx               # System status badge, latency summary, copyright
├── features/                    # Modular feature extensions (auth, telemetry, tools)
├── services/
│   └── api.ts                   # Central API client module with dual-mode offline fallback
├── data.ts                      # Local fallback mock dataset & deterministic RAG fallback
├── types.ts                     # Canonical TypeScript interfaces & enums (FROZEN CONTRACT)
└── App.tsx                      # Main application coordinator & active tab state management
```

### 2.2 Frontend State & API Client Rules
- **Centralized API Calls:** NEVER call `fetch()` or `axios` directly inside UI components. ALL network calls must go through [`frontend/src/services/api.ts`](./frontend/src/services/api.ts).
- **Dual-Mode Graceful Fallback:** If the backend API is offline or unreachable (`TypeError` / network timeout):
  1. Do NOT crash the application or display unhandled blank screens.
  2. Automatically fallback to local data in `frontend/src/data.ts` (`INITIAL_TICKETS`, `getRagResponse`).
  3. Trigger a non-blocking toast warning (`notifyFallback`) to notify the user.
  4. Do NOT swallow intentional HTTP 4xx security/validation errors (e.g., HTTP 400 `PROMPT_SECURITY_VIOLATION` or HTTP 401/403).
- **Language Convention:**
  - **User Interface:** All customer and agent visible labels, placeholders, tooltips, and toast messages must be in **Vietnamese**.
  - **Code & Comments:** Variable names, function names, TypeScript types, and code comments must be in **English**.

### 2.3 UI/UX & Tailwind CSS v4 Guidelines
- Strictly utilize design tokens from [`docs/DESIGN.md`](./docs/DESIGN.md):
  - Brand Primary: `indigo-600` (`#4F46E5`), Hover: `indigo-700` (`#4338CA`)
  - AI Badges / Thinking: `violet-500` (`#8B5CF6`)
  - Caution / Fallback: `amber-500` (`#F59E0B`)
  - Danger / Urgent: `rose-600` (`#E11D48`)
  - Success / Resolved: `emerald-600` (`#059669`)
- Ensure all 4 interaction states are gracefully handled in every view: `Loading`, `Empty`, `Success`, and `Error / Fallback`.

---

## 3. Strict Backend Architecture Rules

### 3.1 Code Structure & Organization
All backend source code is structured under `backend/app/`:
```text
backend/app/
├── core/         # Settings (config.py), externalized prompts (prompts.py), security, exceptions
├── db/           # Async database session (session.py) & declarative Base (base.py)
├── models/       # SQLAlchemy 2.0 ORM models (Ticket, FAQItem, KnowledgeChunk, Workspace, Document, Verification)
├── schemas/      # Pydantic v2 schemas for Request/Response validation (FROZEN CONTRACT)
├── services/     # Business logic (RAG, LLM, Embedding, Fallback, Ticket Copilot, Document, Verification, Agent Tools)
└── api/v1/       # FastAPI APIRouters (chat, tickets, agent, knowledge, workspaces, documents, health)
```

### 3.2 Async/Await & Concurrency
- **Mandatory Async:** All I/O operations (database queries, network requests, Gemini/Ollama API calls) MUST use `async` / `await`. Never block the ASGI event loop with synchronous HTTP calls (`requests.get()` or `time.sleep()`).
- **Connection Pooling:** Database sessions must be managed via FastAPI `Depends(get_db)` yielding async sessions. Background scripts must access `db_session.async_session_factory` via module reference.

### 3.3 Strict Typing & Validation
- **Python Type Hints:** Every function, method parameter, and return value must have explicit type annotations (`from typing import Optional, List, Dict, Any`).
- **Pydantic v2:** All external inputs and outputs must pass through Pydantic v2 models. Never accept raw unvalidated dicts in route handlers.

---

## 4. AI, RAG & Fallback Constraints

### 4.1 Latency Budget & Cost-Guard Circuit Breaker
- **Latency Target:** First token / simple query response target is **< 1,500ms** (p95 < 2,000ms).
- **Timeout Threshold:** External calls to Google Gemini API must timeout at **4.0 seconds max** (`LLM_TIMEOUT_SECONDS=4.0`).
- **Model Fallback Chain:**
  1. Primary Cloud LLM: `gemini-3.5-flash-lite` (automatic retry on `gemini-2.5-flash-lite` if model unavailable).
  2. Local LLM Mode: `qwen2.5:3b` via Ollama when `AI_PROVIDER=ollama`.
  3. Deterministic Non-AI Fallback: If the LLM call times out, returns HTTP 429 (`ResourceExhausted`), or encounters an exception, activate the 60s Cost-Guard cooldown (`cooldown_until = now + 60s`), route immediately to `FallbackService` (BM25 matcher on `seed_faq.json`), and return `"is_fallback": true`.

### 4.2 Grounding, Prompt Management & Safety
- **Externalized Prompts:** System prompts are versioned in `backend/data/prompts.json` and loaded via `backend/app/core/prompts.py`.
- **System Prompt Constraint:** Enforce `temperature: 0.2` for customer-facing RAG. Instruct the model strictly to answer only from provided context or recommend escalating to a human support agent.
- **Citation Badges:** Every RAG-generated answer must extract and return structured source citations (`doc_id`, `title`, `source_url`, `page`, `snippet`).
- **Security & Guardrails:** Incoming queries must pass through `core/security.py` (`sanitize_input`, `check_prompt_injection`). If prompt injection is detected, reject immediately with HTTP 400 (`PROMPT_SECURITY_VIOLATION`).

---

## 5. Ticket Lifecycle, Categories, SLA & Status Mapping Rules

### 5.1 Canonical ID, Priority, Category & SLA Rules
- **Ticket ID Format:** Must follow `#TICK-XXXX` format (e.g., `#TICK-1042`).
- **Urgency / Priority Levels & Canonical SLA Hours:**
  - `Urgent`: **2 hours**
  - `High`: **4 hours**
  - `Medium`: **8 hours**
  - `Low`: **24 hours**
- **Canonical Categories:** `"Authentication"`, `"Billing"`, `"Bug Report"`, `"Feature Request"`, `"General"`.
  - *Alias Rule:* Backend accepts `"Technical Bug"` as a backward-compatible alias and normalizes or maps it alongside `"Bug Report"`.

### 5.2 Status Mapping Between Backend and Frontend
| Lifecycle Phase | Backend Status (DB/API) | Frontend Status (UI/Types) | Color Badge |
| :--- | :--- | :--- | :--- |
| Initial Submission | `"open"` | `"Open"` | Blue (`sky-500`) |
| Under Review / Triaged | `"in_progress"` | `"Pending"` | Amber (`amber-500`) |
| Solved & Approved | `"resolved"` | `"Resolved"` | Emerald (`emerald-600`) |

Use helper functions `mapBackendStatusToFrontend()` and `mapFrontendStatusToBackend()` in `frontend/src/services/api.ts`.

---

## 6. Multi-Agent & Team Collaboration Rules (Strict Conflict Prevention)

1. **Module Ownership Boundaries ("Stay in Your Lane"):**
   - **Owner 1 (AI, RAG & Verification):** Owns `rag_service.py`, `llm_service.py`, `embedding_service.py`, `fallback_service.py`, `verification_service.py`, `agent_tools.py`, `core/prompts.py`, `core/security.py`, `endpoints/chat.py`, `endpoints/documents.py`, `tests/test_rag_module.py`.
   - **Owner 2 (Platform, Auth, Workspaces & Tickets):** Owns `ticket_service.py`, `document_service.py`, `db/session.py`, `models/*`, `endpoints/tickets.py`, `endpoints/agent.py`, `endpoints/workspaces.py`, `endpoints/health.py`, `tests/test_tickets_module.py`, `tests/test_auth_module.py`.
   - **Owner 3 (Frontend UX, DevOps & QA):** Owns `frontend/src/components/*`, `frontend/src/features/*`, `docker-compose.yml`, `.github/workflows/ci.yml`, `docs/*`.
   - **Rule:** Do NOT edit files outside your assigned module without explicit coordination.
2. **Frozen Shared Files Policy:**
   - The following shared integration files may ONLY be modified through the **Integration Owner** (or in dedicated integration commits):
     - `backend/app/api/v1/api.py`, `backend/app/core/config.py`, `backend/app/main.py`
     - `frontend/src/types.ts`, `frontend/src/services/api.ts`, `frontend/src/App.tsx`
     - `docs/API_CONTRACT.md`
3. **Git Branch & Commit Convention:**
   - Branch naming: `feat/<owner>-<module>`, `fix/<owner>-<issue>`, `docs/<owner>-<topic>`.
   - Commit messages MUST follow Conventional Commits: `feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`.
   - NEVER use `git push --force`, `git reset --hard`, or commit `.env` / `*.db` files.
4. **Mandatory Pre-Commit Verification Gate:**
   - Every commit MUST pass both checks with 0 errors before committing:
     - Backend: `$env:GEMINI_API_KEY=""; pytest backend/tests/ -v`
     - Frontend: `npm run lint --prefix frontend && npm run build --prefix frontend`
