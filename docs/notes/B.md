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

---

## 2. Decision Log
- Date: 2026-10-20 — Configured dual-dialect `Vector(768).with_variant(JSON(), "sqlite")` in `models/knowledge.py` to ensure local tests pass without PostgreSQL.
- Date: 2026-10-21 — Implemented HS256 JWT token generation and role-based data isolation on ticket endpoints (`admin` vs `user`), ensuring customers cannot access cross-tenant or other users' support tickets.
