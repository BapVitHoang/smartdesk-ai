# SmartDesk AI - Rules & Guidelines for AI Assistant

This file outlines the foundational technical rules, architecture constraints, and coding standards that every AI assistant must strictly follow when working on the **SmartDesk AI** project.

---

## 1. Project Context & Objectives
- **System Name:** SmartDesk AI (Intelligent Customer Support & Knowledge Synthesizer).
- **Core Architecture:** 
  - **Frontend:** Next.js 14 (React) + Tailwind CSS + Lucide Icons.
  - **Backend:** FastAPI (Python 3.11+) asynchronous ASGI service.
  - **Database:** PostgreSQL 16 with `pgvector` (Fallback: SQLite/In-memory for local testing).
  - **Primary LLM:** Google Gemini 1.5 Flash (`gemini-1.5-flash`), embeddings via `text-embedding-004`.
  - **Deterministic Non-AI Fallback:** Keyword/BM25 FAQ matcher on curated dataset.

---

## 2. Strict Backend Architecture Rules

### 2.1 Code Structure & Organization
All backend source code must be structured cleanly under `backend/app/`:
```text
backend/app/
├── core/         # Settings (pydantic-settings), security, global exception handlers
├── db/           # Async database session & base declarative models
├── models/       # SQLAlchemy 2.0 ORM models (Ticket, FAQ, Conversation, VectorChunk)
├── schemas/      # Pydantic v2 schemas for Request/Response validation
├── services/     # Pure business logic (RAG, Gemini LLM, Fallback, Ticket Triage)
└── api/v1/       # FastAPI APIRouters (chat, tickets, agent, knowledge, health)
```

### 2.2 Async/Await & Concurrency
- **Mandatory Async:** All I/O operations (database queries, network requests, Gemini API calls, file reads) MUST use `async` / `await`. Never block the ASGI event loop with synchronous calls (e.g., use `httpx.AsyncClient` instead of `requests`).
- **Connection Pooling:** Database sessions must be managed via FastAPI `Depends()` yielding async sessions.

### 2.3 Strict Typing & Validation
- **Python Type Hints:** Every function, method parameter, and return value must have explicit type annotations (`from typing import Optional, List, Dict, Any`).
- **Pydantic v2:** All external inputs and outputs must pass through Pydantic v2 models. Never accept raw unvalidated dicts in route handlers.
- **No Mock Placeholders:** Do NOT leave unfinished placeholders like `TODO: implement later` or pass empty functions without functional implementation.

---

## 3. AI, RAG & Fallback Constraints

### 3.1 Latency Budget & Circuit Breaker
- **Latency Target:** First token / simple query response target is **< 1,500ms** (p95 < 2,000ms).
- **Timeout Threshold:** External calls to Google Gemini API must timeout at **4.0 seconds max**.
- **Deterministic Fallback Trigger:** If the LLM call times out, returns HTTP 429/500, or returns a confidence score below threshold:
  1. Catch the exception gracefully without failing the client request.
  2. Route immediately to `FallbackService` (keyword/BM25 matcher on `seed_faq.json`).
  3. Return response with `"is_fallback": true` and pre-populated ticket escalation payload.

### 3.2 Grounding & Prompt Safety
- **System Prompt Constraint:** Enforce `temperature: 0.2` for customer-facing RAG. Instruct the model strictly: *"If the provided context does not contain enough information to answer truthfully, explicitly say you do not know and recommend escalating to a human support agent."*
- **Citation Badges:** Every RAG-generated answer must extract and return structured source citations (`doc_id`, `title`, `source_url` or section).
- **Basic Guardrails:** Check and sanitize incoming chat prompts against prompt injection tokens before passing to LLM.

---

## 4. Ticket Lifecycle & Triage Rules
- **Ticket ID Format:** Must follow `#TICK-XXXX` format (e.g., `#TICK-1042`).
- **Urgency Levels:** Exactly 4 allowed values: `Low`, `Medium`, `High`, `Urgent`.
- **Status Lifecycle:** `open` -> `in_progress` -> `resolved` (or `closed`).
- **AI Agent Copilot:** When creating or inspecting a ticket:
  - Generate automatic tags (e.g. `["Authentication", "Urgent"]`).
  - Pre-generate an `ai_draft_reply` that support agents can review, edit, and approve.

---

## 5. Testing & Verification Rules
- Every newly created endpoint must have at least one automated unit/integration test using `pytest` and `httpx.AsyncClient`.
- Provide a reproducible health check endpoint `GET /api/v1/health` and smoke test `GET /api/v1/health/smoke-test` to benchmark real-time latency.
