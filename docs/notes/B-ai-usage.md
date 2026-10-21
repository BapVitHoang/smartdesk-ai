# Developer B — AI Usage & Prompting Log

> Required by **REQ-28** and evaluated under **CRIT-06** & **CRIT-09**.  
> Every AI-assisted code generation session must be recorded below.
> **Rule:** Record every real AI mistake you find, with the commit hash; never invent one.

---

### Session 1: OAuth2 Authentication, HS256 JWT & RBAC Data Isolation (`TASK-12`)
- **Date:** 2026-10-21
- **AI Tool Used:** Antigravity AI Assistant
- **Key Prompt:** "Hoàn thiện Task B1: Xác thực OAuth2 + HS256 JWT, Phân quyền RBAC (admin/user) & Cô lập dữ liệu trong auth.py, deps.py, tickets.py và agent.py."
- **Manual Verification & Changes:**
  - Manually verified PyJWT HS256 token generation and backward-compatibility with `demo_jwt_token_for_{email}`.
  - Verified customer ticket filtering: customer `an.nguyen@company.vn` only sees their own tickets.
- **AI Mistakes & Corrections (if encountered):**
  - *Observed Issue:* When testing `admin_client` and `user_client` together in `test_rbac_ticket_isolation_and_admin_only_routes`, the two pytest fixtures conflicted on `app.dependency_overrides[get_current_user]`. The `user_client` fixture ran second and clobbered the override, causing the subsequent admin DELETE call to run with user permissions and fail with 403.
  - *File:* `backend/tests/test_auth_module.py`
  - *Fix Applied:* Switched test to generate real HS256 JWTs via `/api/v1/auth/oauth2/login` and dispatched them via explicit `Authorization: Bearer <token>` headers using `unauth_client`, ensuring true end-to-end token validation without dependency override collisions.

---

### Session 2: Server-side Sorting, Pagination Header & Workspace Deletion (`TASK-13`)
- **Date:** 2026-10-21
- **AI Tool Used:** Antigravity AI Assistant
- **Key Prompt:** "Bổ sung DELETE, Server-Side Sorting, Pagination Header X-Total-Count & Kết nối Copilot trong ticket_service.py, tickets.py, workspaces.py."
- **Manual Verification & Changes:**
  - Verified `sort_by` (`priority`, `status`, `sla_hours`, `created_at`) and `sort_order` (`asc`, `desc`).
  - Verified `DELETE /api/v1/workspaces/1` returns `HTTP 400 Bad Request` while custom workspaces return `HTTP 204 No Content`.
- **AI Mistakes & Corrections (if encountered):**
  - *Observed Issue:* The initial count query `select(func.count(Ticket.id))` did not apply the same customer email or filter clauses as the main query, which would cause customer requests to return the total ticket count of the whole database in `X-Total-Count` instead of their filtered count.
  - *File:* `backend/app/api/v1/endpoints/tickets.py`
  - *Fix Applied:* Replicated all active where clauses (RBAC user filter, workspace filter, status, category, priority, and text search) into `count_query`.

---

### Session 3: Dual-Dialect pgvector and PII Masking on Embeddings (`TASK-14`)
- **Date:** 2026-10-21
- **AI Tool Used:** Antigravity AI Assistant
- **Key Prompt:** "Kích hoạt Dual-Dialect pgvector trên PostgreSQL trong knowledge.py, session.py, embedding_service.py và hoàn thiện test platform."
- **Manual Verification & Changes:**
  - Verified `Vector(768).with_variant(JSON(), "sqlite")` compatibility across SQLite and PostgreSQL.
  - Verified `redact_pii()` mask is applied before embedding API calls.
  - Verified `docker compose config` parses without syntax errors.
