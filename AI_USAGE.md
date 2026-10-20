# AI Usage, Verification & Engineering Log (`AI_USAGE.md`)

> **Project:** SmartDesk AI – Intelligent Customer Support & Knowledge Synthesizer  
> **Requirement Alignment:** `REQ-28` / `CRIT-09` (Mandatory AI Usage Disclosure, Verification Protocol, and Real Failure/Fix Case Studies)

---

## 1. AI Tools & Models Used During Development

| Tool / Model | Role in Development | Scope of Usage |
| :--- | :--- | :--- |
| **Google Antigravity / Claude / Gemini Coding Assistants** | Architecture auditing, FastAPI async scaffolding, React 19 + Tailwind CSS v4 component implementation, and Pytest test generation. | Used under strict human supervision governed by [`AGENTS.md`](./AGENTS.md) and [`.cursorrules`](./.cursorrules). |
| **Google Gemini (`gemini-3.5-flash-lite` & `gemini-2.5-flash-lite`)** | Runtime cloud LLM for grounded customer RAG (`rag_service.py`), ticket copilot drafting (`ticket_service.py`), and 3-stage knowledge verification (`verification_service.py`). | Replaced retired `gemini-1.5-flash` after live API verification. |
| **Google `gemini-embedding-001`** | Runtime cloud vector embedding model for `KnowledgeChunk` and `FAQItem` semantic indexing. | Replaced retired `text-embedding-004`. |
| **Local Ollama (`qwen2.5:3b` & `nomic-embed-text`)** | Local, zero-cost AI provider for offline development, evaluation benchmarks, and rate-limit-free demonstrations. | Integrated in `llm_service.py` and `embedding_service.py` (`AI_PROVIDER=ollama`). |

---

## 2. Human Verification Workflow (How AI-Generated Code Was Audited)

Every piece of AI-assisted code or configuration was subjected to a 4-gate verification protocol before acceptance:
1. **Contract & Type Gate:** Checked against frozen Pydantic v2 schemas (`backend/app/schemas/`) and TypeScript interfaces (`frontend/src/types.ts` + `npm run lint --prefix frontend`).
2. **Live API & Model Probe Gate:** Never trusted training-cutoff model names from AI assistants; verified actual model availability against `genai.Client().models.get()` and local Ollama endpoints.
3. **Automated Integration Test Gate:** Executed `pytest backend/tests/ -v` across online, offline (`GEMINI_API_KEY=""`), and simulated rate-limit (`HTTP 429`) conditions.
4. **Security & Edge-Case Gate:** Tested prompt injection patterns (`core/security.py`), cross-workspace RAG isolation (`workspace_id`), and CWD-independent path resolution.

---

## 3. Real Failure & Human Fix Case Studies From This Repository

### Case Study 1: Retired Google Gemini Model Names (`gemini-1.5-flash` & `text-embedding-004` Returning HTTP 404)
- **What the AI Assistant Generated:** Initial AI-assisted scaffolding configured `LLM_MODEL_NAME = "gemini-1.5-flash"` and `EMBEDDING_MODEL_NAME = "text-embedding-004"` based on historical documentation.
- **Why It Failed (Evidence):** When tested against the live Google GenAI SDK (`google-genai`), both `models/gemini-1.5-flash` and `models/text-embedding-004` returned `404 NOT_FOUND` (`is not found for API version v1beta`), causing every live RAG query to trip the circuit breaker and fall back to BM25.
- **How We Diagnosed & Fixed It (Commit `8c64aa6` + Foundation Hardening):**
  1. Ran a live diagnostic probe against `client.models.get()` to enumerate active models.
  2. Updated `backend/app/core/config.py` to use `gemini-3.5-flash-lite` (primary LLM) and `gemini-embedding-001` (embeddings), and added an automatic secondary cloud model fallback (`gemini-2.5-flash-lite`) inside `backend/app/services/llm_service.py`.
  3. Verified live round-trip latency at `922.74 ms` (`PASS`).

### Case Study 2: SQLite Relative Path Drift & Session Re-Binding in Standalone Scripts
- **What the AI Assistant Generated:** AI-generated code used a relative SQLite URL (`sqlite+aiosqlite:///./smartdesk.db`), relative sample document paths (`Path("backend/data") / rel_path`), and imported `from app.db.session import async_session_factory` by value in `backend/scripts/reembed_chunks.py` and `export_finetune_dataset.py`.
- **Why It Failed (Evidence):**
  1. Running `pytest` or scripts from the repo root created a duplicate `./smartdesk.db` in the project root while `uvicorn` running inside `backend/` read `backend/smartdesk.db`.
  2. When PostgreSQL failed and `init_db()` rebound `session.async_session_factory` to SQLite, scripts that had imported `async_session_factory` by value still held the broken PostgreSQL factory reference.
- **How We Diagnosed & Fixed It (Commit `4dfd685` + Restructure Cleanup):**
  1. Added `BACKEND_DIR` path resolution in `backend/app/core/config.py` (`resolve_sqlite_path` validator) so `smartdesk.db` always resolves to `backend/smartdesk.db` regardless of working directory.
  2. Anchored sample document seeding in `backend/app/db/session.py` to `BACKEND_DIR / "data" / rel_path`.
  3. Updated `reembed_chunks.py` and `export_finetune_dataset.py` to reference `db_session.async_session_factory` via module attribute after `await db_session.init_db()`.

### Case Study 3: Free-Tier Rate Limit (HTTP 429) Cascade During Document Verification
- **What the AI Assistant Generated:** The initial document ingestion and 3-stage verification pipeline called Gemini embeddings sequentially for every chunk and then fired multiple LLM calls for Synthetic QA generation, RAG self-testing, and AI Judge scoring without rate-limit state tracking.
- **Why It Failed (Evidence):** Uploading a multi-page document and clicking "Verify" exceeded Google Gemini Free Tier's 15 RPM quota (`HTTP 429 ResourceExhausted`), causing subsequent requests to hang or fail and risking frontend timeout (`5000ms`).
- **How We Diagnosed & Fixed It (Commit `4abcf8c`):**
  1. Implemented a stateful **Cost-Guard Circuit Breaker** (`cooldown_until = time.time() + 60.0`) in `llm_service.py` and `embedding_service.py` that immediately stops external API calls for 60 seconds upon any HTTP 429 and switches to deterministic 768-dim SHA-256 unit pseudo-vectors and local BM25 fallback.
  2. Parallelized `run_rag_self_test` with `asyncio.gather()` and added `AI_PROVIDER=ollama` (`qwen2.5:3b` + `nomic-embed-text`) for unlimited local execution.

---

## 4. Planned AI Engineering Extensions (`TODO` for Phase B–D Execution)
- [ ] `TODO (Phase B - TASK-B04)`: Log AI Usage Diary entries for SSE Token Streaming (`/api/v1/chat/stream`) and Agent Tool Calling (`agent_tools.py`).
- [ ] `TODO (Phase C - TASK-C02)`: Attach before-vs-after benchmark table from `backend/scripts/run_eval.py` (24-case evaluation dataset across Default, SmileCare, and TechStore workspaces).
