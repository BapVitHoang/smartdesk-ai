# SmartDesk AI - Intelligent Customer Support & Knowledge Synthesizer

> **Project:** SmartDesk AI  
> **Course / Deliverable:** Homework 3B - Complete Frontend & Backend Prototype  
> **Tech Stack:** Next.js 14 / React 19 + Tailwind CSS (Frontend) & FastAPI Async + Google Gemini 1.5 Flash + SQLAlchemy 2.0 (Backend)

---

## 1. Project Overview

**SmartDesk AI** is an intelligent customer support automation platform designed to solve the two biggest operational hurdles in modern helpdesks: slow agent turnaround times and inaccurate, hallucinated AI responses.

### Key Capabilities:
- **Customer AI Chat Assistant with Grounded Citations:** Employs RAG with Google Gemini 1.5 Flash to synthesize answers backed by verified documentation (`[Doc #ID: Title]`).
- **Deterministic Circuit Breaker (< 4.0s):** If the external LLM times out or encounters rate limits (HTTP 429), the system immediately engages a pure-Python BM25 keyword matching engine on `seed_faq.json` with zero customer disruption.
- **Support Ticket Triage & AI Copilot:** Auto-classifies inquiries with `#TICK-XXXX` codes, detects keywords to assign AI tags (`Authentication`, `Urgent`, `2FA Recovery`), computes SLA deadlines, and drafts personalized resolution responses for human agent review.

---

## 2. System Architecture & Directory Structure

```text
smartdesk-ai/
├── src/                            # Next.js / React Frontend Application
│   ├── components/                 # Header, ChatView, TicketFormView, AgentDashboardView
│   ├── App.tsx                     # Main layout & UI state coordinator
│   ├── data.ts                     # Mock datasets & initial states
│   └── types.ts                    # TypeScript interfaces
├── backend/                        # FastAPI Asynchronous ASGI Backend
│   ├── app/
│   │   ├── api/v1/endpoints/       # chat.py, tickets.py, agent.py, health.py
│   │   ├── core/                   # config.py, security.py, exceptions.py
│   │   ├── db/                     # session.py, base.py
│   │   ├── models/                 # ticket.py, knowledge.py
│   │   ├── schemas/                # chat.py, ticket.py, health.py
│   │   ├── services/               # llm_service.py, fallback_service.py, rag_service.py, ticket_service.py
│   │   └── main.py                 # ASGI application & CORS middleware
│   ├── data/
│   │   └── seed_faq.json           # 12 Curated FAQ articles for BM25 Fallback & DB Seed
│   ├── tests/
│   │   └── test_api.py             # Pytest automated test suite (httpx.AsyncClient)
│   ├── .env.example                # Backend environment template
│   ├── Dockerfile                  # Production container configuration
│   └── requirements.txt            # Python dependencies
├── API_CONTRACT.md                 # Complete API Request/Response specifications
├── TEST_ACCEPTANCE.md              # 8 Automated tests & 4 Manual acceptance test scenarios
└── README.md                       # Main project documentation & execution guide
```

---

## 3. Configuration & Environment Setup

All configuration settings are centralized via environment variables.

### 3.1 Backend Configuration (`backend/.env`)
Copy the example file:
```bash
cd backend
cp .env.example .env
```
Key configuration properties:
- `GEMINI_API_KEY`: Google Gemini API key obtained from [Google AI Studio](https://aistudio.google.com/). *(Optional: Fallback engine activates automatically if omitted)*.
- `DATABASE_URL`: `sqlite+aiosqlite:///./smartdesk.db` (Default SQLite Async) or `postgresql+asyncpg://user:pass@localhost:5432/smartdesk`.
- `LLM_TIMEOUT_SECONDS`: `4.0` (Strict SLA threshold).
- `CORS_ORIGINS`: Allowed origins, e.g. `["http://localhost:3000","http://localhost:5173"]`.

### 3.2 Frontend Configuration (`.env.local`)
Create `.env.local` in the project root:
```bash
cp .env.example .env.local
```
- `GEMINI_API_KEY`: Optional client-side key if testing direct generative features.
- `VITE_API_URL`: `http://localhost:8000/api/v1`

---

## 4. How to Run

### 4.1 Running the Backend (FastAPI)
Prerequisite: Python 3.11+
```bash
# 1. Navigate to backend directory
cd backend

# 2. Install dependencies
pip install -r requirements.txt

# 3. Start Uvicorn ASGI server with live reloading
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
- API Base URL: `http://localhost:8000/api/v1`
- Interactive OpenAPI Docs: `http://localhost:8000/docs`
- Service Health Probe: `http://localhost:8000/api/v1/health`

### 4.2 Running the Frontend (Next.js / Vite React)
Prerequisite: Node.js 18+
```bash
# 1. From the project root
npm install

# 2. Start frontend dev server
npm run dev
```
Open your browser and navigate to `http://localhost:3000`.

---

## 5. Testing & Verification

### 5.1 Automated Pytest Suite
Run the backend test suite:
```bash
cd backend
pytest tests/ -v
```
All 8 automated tests verify:
1. `test_health_check`: Readiness probe and database ping.
2. `test_smoke_test`: LLM round-trip latency measurement.
3. `test_chat_rag_and_fallback`: Grounded answering with citations.
4. `test_chat_prompt_injection_guardrail`: Security input filtering.
5. `test_create_ticket_with_copilot_triage`: `#TICK-XXXX` generation, auto-tagging, SLA calculation.
6. `test_list_and_filter_tickets`: Category/priority querying.
7. `test_update_ticket_and_customize_draft`: Agent draft reply customization.
8. `test_agent_copilot_regenerate_draft`: AI draft regeneration.

### 5.2 Manual Acceptance Tests
See [TEST_ACCEPTANCE.md](TEST_ACCEPTANCE.md) for step-by-step test scripts covering:
- Scenario 1: Customer RAG Inquiry with Grounded Citations.
- Scenario 2: AI Outage / Timeout & Deterministic Fallback Trigger.
- Scenario 3: Customer Ticket Creation with Form Validation.
- Scenario 4: Support Agent Triage Dashboard & AI Copilot Draft Customization.

---

## 6. Homework 3B Submission Evidence Checklist

| Requirement | Artifact / Evidence Location | Status |
| :--- | :--- | :--- |
| **Runnable Frontend Prototype** | `src/` (Chat, Ticket Form, Agent Dashboard) at `http://localhost:3000` | Completed |
| **Runnable FastAPI Backend** | `backend/app/` (FastAPI 100% Async) at `http://localhost:8000` | Completed |
| **API Contract Definitions** | [API_CONTRACT.md](API_CONTRACT.md) with sample request & response bodies | Completed |
| **Test Evidence (Automated & Manual)**| [TEST_ACCEPTANCE.md](TEST_ACCEPTANCE.md) & `backend/tests/test_api.py` | Completed |
| **Run & Configuration Instructions** | Sections 3 & 4 of this [README.md](README.md) | Completed |
| **Commit Hash** | Recorded in Git version control history | See below |

---

## 7. Submission Commit Hash

To view the exact submission commit hash:
```bash
git rev-parse HEAD
```
