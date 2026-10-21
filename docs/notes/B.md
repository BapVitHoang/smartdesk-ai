# Developer B — Technical Notes & Decisions

> Workstream: Platform, Data & Security (`feature/b-platform`)  
> Owner: Developer B

## 1. Ongoing Implementation Notes

### Task B1: OAuth2 Authentication, HS256 JWT, and RBAC Implementation (`TASK-12` / `REQ-06`, `REQ-09`, `REQ-36`)
1. **Pydantic v2 Schemas (`backend/app/schemas/auth.py`):**
   - Implemented `OAuth2LoginRequest` supporting both Google ID Token (`credential`) and seeded Demo account (`email`).
   - Implemented `OAuth2PasswordRequest` for standard username/password grant.
   - Defined `TokenResponse` and `UserProfileResponse`.
2. **Real HS256 JWT Issuance & Verification:**
   - In `backend/app/api/v1/endpoints/auth.py`: Implemented `create_access_token` using PyJWT with expiration claims (`exp`, `iat`, `sub`, `role`, `user_id`, `workspace_id`).
   - In `backend/app/core/deps.py`: Updated `get_current_user` to decode and verify JWT tokens against `settings.JWT_SECRET_KEY` while retaining backward-compatibility for legacy demo tokens (`demo_jwt_token_for_{email}`).
3. **RBAC & Customer Data Isolation:**
   - In `backend/app/api/v1/endpoints/tickets.py`:
     - Regular customers (`role != "admin"`) only see their own tickets (`customer_email == current_user.email`).
     - Regular customers attempting to read another user's ticket details are rejected with `HTTP 403 Forbidden`.
     - `PATCH /tickets/{id}` and `DELETE /tickets/{id}` are strictly guarded by `require_role("admin")`.
   - In `backend/app/api/v1/endpoints/agent.py`:
     - Copilot draft regeneration (`/agent/tickets/{id}/generate-draft`) is strictly restricted to `admin` role.
4. **Automated Test Coverage:**
   - Extended `backend/tests/test_auth_module.py` with 6 dedicated test cases covering login, token resolution, 401 unauthorized handling, and RBAC data isolation. All 49 test cases pass (100%).

### Task B2: Server-Side Sorting, Pagination Count Header, Delete API & Copilot Integration (`TASK-13` / `REQ-15`, `REQ-30`, `REQ-31`)
1. **Single-Call Copilot Integration (`backend/app/services/ticket_service.py`):**
   - Connected `ticket_copilot_service.generate_ticket_triage_and_draft()` in `create_ticket()` and `generate_draft_reply()` to obtain structured classification, tag extraction, and localized Vietnamese draft replies.
2. **Server-Side Sorting & Pagination Header (`backend/app/api/v1/endpoints/tickets.py`):**
   - Added `sort_by` (`created_at`, `priority`, `status`, `sla_hours`) and `sort_order` (`asc`, `desc`) query parameters to `GET /api/v1/tickets`.
   - Added count calculation matching current user and filter criteria, returning total records via `X-Total-Count` response header.
3. **Delete Endpoints (`tickets.py` & `workspaces.py`):**
   - `DELETE /api/v1/tickets/{ticket_id}`: Admin-only deletion returning `HTTP 204 No Content`.
   - `DELETE /api/v1/workspaces/{id}`: Admin-only deletion returning `HTTP 204 No Content`. Explicitly guards default workspace (ID=1) with `HTTP 400 Bad Request`.
4. **Automated Test Coverage:**
   - Extended `backend/tests/test_tickets_module.py` with 3 test cases for sorting, `X-Total-Count` header, workspace deletion rules, and copilot triage integration. All 52 tests pass (100%).

### Task B3 & B4: Dual-Dialect pgvector, PII Redaction & Platform Verification (`TASK-14` / `REQ-07`, `REQ-11`, `REQ-28`, `REQ-38`)
1. **Dual-Dialect pgvector Mapping (`backend/app/models/knowledge.py`):**
   - Configured `Vector(768).with_variant(JSON(), "sqlite")` from `pgvector.sqlalchemy` for `KnowledgeChunk.embedding` and `FAQItem.embedding`.
2. **PostgreSQL Extension Initialization (`backend/app/db/session.py`):**
   - Added automatic execution of `CREATE EXTENSION IF NOT EXISTS vector` on engine startup when PostgreSQL is detected.
3. **PII Masking & Dual-Mode Vector Search (`backend/app/services/embedding_service.py`):**
   - Enforced `redact_pii(text)` sanitization before dispatching queries to external Google Gemini / Ollama Embedding APIs.
   - Enhanced `search_similar_chunks()`: If running on PostgreSQL, dispatches native SQL pgvector cosine distance query (`<=>` operator); if running on SQLite, falls back seamlessly to in-memory cosine similarity calculation.
4. **Platform Automated Test Suite (`backend/tests/platform/test_pgvector_and_db.py`):**
   - Added tests verifying dual-dialect mapping, PII masking, and SQLite fallback similarity.
5. **Docker Compose Verification:**
   - Validated `docker compose config` with `postgres: pgvector/pgvector:pg16`, `backend`, and `frontend`.
6. **AI Usage & Prompting Log (`docs/notes/B-ai-usage.md`):**
   - Documented all 3 sessions and real bug diagnostics.

---

## 2. Decision Log
- Date: 2026-10-20 — Configured dual-dialect `Vector(768).with_variant(JSON(), "sqlite")` in `models/knowledge.py` to ensure local tests pass without PostgreSQL.
- Date: 2026-10-21 — Implemented HS256 JWT token generation and role-based data isolation on ticket endpoints (`admin` vs `user`), ensuring customers cannot access cross-tenant or other users' support tickets.
- Date: 2026-10-21 — Added `X-Total-Count` header and server-side sorting to `GET /api/v1/tickets`, hooked up `ticket_copilot_service` into ticket creation, and guarded workspace deletion (`id=1` blocked).
- Date: 2026-10-21 — Enabled native pgvector SQL cosine search with SQLite in-memory fallback, and masked PII before calling external embedding APIs.
