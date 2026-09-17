# SmartDesk AI - Rules & Guidelines for AI Assistant

This file outlines the foundational technical rules, architecture constraints, and coding standards that every AI assistant must strictly follow when working on the **SmartDesk AI** project.

---

## 1. Project Context & Mandatory Document Index

### 1.1 Core Architecture
- **System Name:** SmartDesk AI (Intelligent Customer Support & Knowledge Synthesizer).
- **Frontend:** React 19 + Vite 6 + Tailwind CSS v4 + TypeScript + Lucide Icons + Motion (Single Page Application, NOT Next.js).
- **Backend:** FastAPI (Python 3.11+) asynchronous ASGI service.
- **Database:** PostgreSQL 16 with `pgvector` (Fallback: SQLite/In-memory for local testing).
- **Primary LLM:** Google Gemini 1.5 Flash (`gemini-1.5-flash`), embeddings via `text-embedding-004`.
- **Deterministic Non-AI Fallback:** Keyword/BM25 FAQ matcher on curated dataset (`backend/data/seed_faq.json`).

### 1.2 Mandatory Document Reference Index
Before implementing any task, the AI assistant MUST consult the following canonical documents:
1. **API Specifications & Schemas:** [`API_CONTRACT.md`](./API_CONTRACT.md) - Contains full request/response schemas, error codes, and HTTP status contracts.
2. **UI/UX & Design Tokens:** [`DESIGN.md`](./DESIGN.md) - Contains brand colors, typography hierarchy, UI state handling, and component specs.
3. **Acceptance Test Matrix:** [`TEST_ACCEPTANCE.md`](./TEST_ACCEPTANCE.md) - Contains the 4 core acceptance test scenarios and automated verification instructions.
4. **General Overview & Startup:** [`README.md`](./README.md) - Quickstart guide and Windows batch script definitions (`start.bat`, `start_all.bat`, `start_backend.bat`).

---

## 2. Strict Frontend Architecture Rules

### 2.1 Code Structure & Organization
All frontend code is strictly structured under `src/`:
```text
src/
├── components/           # Presentational & interactive UI views
│   ├── Header.tsx        # Top navigation, active tab switcher, demo state switcher
│   ├── ChatView.tsx      # Customer RAG chat, citation badges, quick prompts
│   ├── TicketFormView.tsx# Ticket submission form, SLA preview, live validation
│   ├── AgentDashboardView.tsx # Agent triage table, filtering, AI copilot draft review
│   └── Footer.tsx        # System status badge, latency summary, copyright
├── services/
│   └── api.ts            # Central API client module with dual-mode offline fallback
├── data.ts               # Local fallback mock dataset & deterministic RAG fallback
├── types.ts              # Canonical TypeScript interfaces & enums
└── App.tsx               # Main application coordinator & active tab state management
```

### 2.2 Frontend State & API Client Rules
- **Centralized API Calls:** NEVER call `fetch()` or `axios` directly inside UI components. ALL network calls must go through [`src/services/api.ts`](./src/services/api.ts).
- **Dual-Mode Graceful Fallback:** If the backend API is offline or unreachable:
  1. Do NOT crash the application or display unhandled blank screens.
  2. Automatically fallback to local data in `src/data.ts` (`INITIAL_TICKETS`, `getRagResponse`).
  3. Trigger a non-blocking toast warning (`notifyFallback`) to notify the user.
- **Language Convention:** 
  - **User Interface:** All customer and agent visible labels, placeholders, tooltips, and toast messages must be in **Vietnamese**.
  - **Code & Comments:** Variable names, function names, TypeScript types, and code comments must be in **English**.

### 2.3 UI/UX & Tailwind CSS v4 Guidelines
- Strictly utilize design tokens from [`DESIGN.md`](./DESIGN.md):
  - Brand Primary: `indigo-600` (`#4F46E5`), Hover: `indigo-700` (`#4338CA`)
  - AI Badges / Thinking: `violet-500` (`#8B5CF6`)
  - Caution / Fallback: `amber-500` (`#F59E0B`)
  - Danger / Urgent: `rose-600` (`#E11D48`)
  - Success / Resolved: `emerald-600` (`#059669`)
- Ensure all 4 interaction states are gracefully handled in every view: `Loading`, `Empty`, `Success`, and `Error / Fallback`.

---

## 3. Strict Backend Architecture Rules

### 3.1 Code Structure & Organization
All backend source code must be structured cleanly under `backend/app/`:
```text
backend/app/
├── core/         # Settings (pydantic-settings), security (prompt injection), exceptions
├── db/           # Async database session & base declarative models
├── models/       # SQLAlchemy 2.0 ORM models (Ticket, FAQItem, KnowledgeChunk)
├── schemas/      # Pydantic v2 schemas for Request/Response validation
├── services/     # Pure business logic (RAG, Gemini LLM, Fallback, Ticket Copilot)
└── api/v1/       # FastAPI APIRouters (chat, tickets, agent, knowledge, health)
```

### 3.2 Async/Await & Concurrency
- **Mandatory Async:** All I/O operations (database queries, network requests, Gemini API calls, file reads) MUST use `async` / `await`. Never block the ASGI event loop with synchronous calls (use `httpx.AsyncClient` instead of `requests`).
- **Connection Pooling:** Database sessions must be managed via FastAPI `Depends()` yielding async sessions.

### 3.3 Strict Typing & Validation
- **Python Type Hints:** Every function, method parameter, and return value must have explicit type annotations (`from typing import Optional, List, Dict, Any`).
- **Pydantic v2:** All external inputs and outputs must pass through Pydantic v2 models. Never accept raw unvalidated dicts in route handlers.
- **No Mock Placeholders:** Do NOT leave unfinished placeholders like `TODO: implement later` or pass empty functions without functional implementation.

---

## 4. AI, RAG & Fallback Constraints

### 4.1 Latency Budget & Circuit Breaker
- **Latency Target:** First token / simple query response target is **< 1,500ms** (p95 < 2,000ms).
- **Timeout Threshold:** External calls to Google Gemini API must timeout at **4.0 seconds max**.
- **Deterministic Fallback Trigger:** If the LLM call times out, returns HTTP 429/500, or encounters an exception:
  1. Catch the exception gracefully without failing the client request.
  2. Route immediately to `FallbackService` (keyword/BM25 matcher on `seed_faq.json`).
  3. Return response with `"is_fallback": true` and pre-populated ticket escalation payload.

### 4.2 Grounding & Prompt Safety
- **System Prompt Constraint:** Enforce `temperature: 0.2` for customer-facing RAG. Instruct the model strictly: *"If the provided context does not contain enough information to answer truthfully, explicitly say you do not know and recommend escalating to a human support agent."*
- **Citation Badges:** Every RAG-generated answer must extract and return structured source citations (`doc_id`, `title`, `source_url` or section).
- **Security & Guardrails:** Incoming queries must pass through `core/security.py` (`sanitize_input`, `check_prompt_injection`). If prompt injection is detected, reject immediately with HTTP 400 (`PROMPT_SECURITY_VIOLATION`).

---

## 5. Ticket Lifecycle & Status Mapping Rules

### 5.1 ID Format & Urgency Levels
- **Ticket ID Format:** Must follow `#TICK-XXXX` format (e.g., `#TICK-1042`).
- **Urgency Levels:** Exactly 4 allowed values: `Low`, `Medium`, `High`, `Urgent`.

### 5.2 Status Mapping Between Backend and Frontend
The AI assistant must respect the canonical mapping between Backend and Frontend statuses:

| Lifecycle Phase | Backend Status (DB/API) | Frontend Status (UI/Types) | Color Badge |
| :--- | :--- | :--- | :--- |
| Initial Submission | `"open"` | `"Open"` | Blue (`sky-500`) |
| Under Review / Triaged | `"in_progress"` | `"Pending"` | Amber (`amber-500`) |
| Solved & Approved | `"resolved"` | `"Resolved"` | Emerald (`emerald-600`) |

Use helper functions `mapBackendStatusToFrontend()` and `mapFrontendStatusToBackend()` in `src/services/api.ts` to convert between layers.

### 5.3 AI Agent Copilot Rules
When creating or inspecting a ticket:
- Automatically generate tags (e.g. `["Authentication", "Urgent"]`).
- Pre-generate an `ai_draft_reply` that support agents can review, edit, and approve before sending.
- Never auto-send an AI draft reply to the customer without human agent approval.

---

## 6. Testing, Verification & Startup Rules

### 6.1 Automated Testing
- Backend endpoints must be verified with `pytest backend/tests/ -v`.
- Frontend must pass TypeScript check `npm run lint` and build check `npm run build`.
- Real-time latency benchmark must pass via `GET /api/v1/health/smoke-test`.

### 6.2 Environment & Secrets Safety
- NEVER commit `.env` containing real `GEMINI_API_KEY` into Git.
- Backend loads secrets via `backend/app/core/config.py` from `.env`.
- Frontend reads backend endpoint from `import.meta.env.VITE_API_URL` (default: `http://localhost:8000/api/v1`).
- Windows users launch the project using `start.bat` (Frontend), `start_backend.bat` (Backend), or `start_all.bat` (Both).
