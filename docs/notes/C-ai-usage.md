# Developer C — AI Usage & Prompting Log

> Required by **REQ-28** and evaluated under **CRIT-06** & **CRIT-09**.  
> Every AI-assisted code generation session must be recorded below.
> **Rule:** Record every real AI mistake you find, with the commit hash; never invent one.

---

## Session 1: SSE Token Streaming UI & Confirmation Card (Task C1)
- **Date:** 2026-10-21
- **AI Tool Used:** Antigravity / Gemini 3.5 Flash (Advanced Agentic Assistant)
- **Key Prompt:** "Implement SSE token streaming in ChatView.tsx with pulsing cursor, violet tool call badges, and an interactive Vietnamese Two-Phase Confirmation Card for pending mutating actions calling POST /api/v1/chat/confirm-action."
- **Manual Verification & Changes:**
  - Verified event stream handler (`onmessage`) in `frontend/src/services/api/chat.ts` parsing `token`, `metadata`, and `done` events.
  - Ensured UI correctly displays `PendingAction` card with `confirmChatAction(actionId, confirmed)` handling.
  - Verified `npm run lint` and `npm run build` completed with zero errors.
- **AI Mistakes & Corrections:**
  - *Observed Issue:* AI initially assumed `POST /api/v1/chat/stream` only emitted string tokens without parsing structured metadata JSON for `pending_action`.
  - *Commit Hash / File:* `frontend/src/services/api/chat.ts` (Commit `421ab4f`)
  - *Fix Applied:* Manually added a JSON parser block for `event: metadata` and `event: done` to extract `pending_action` and `tools_called` arrays.

---

## Session 2: Admin AI Telemetry & Cost-Guard Cooldown Reset (Task C2)
- **Date:** 2026-10-21
- **AI Tool Used:** Antigravity / Gemini 3.5 Flash
- **Key Prompt:** "Connect TelemetryPanel.tsx to GET /api/v1/agent/ai-usage and POST /api/v1/agent/ai-usage/reset-cooldown. Embed the panel inside AgentDashboardView with a view switcher tab."
- **Manual Verification & Changes:**
  - Verified `getAiUsageSummary()` and `resetAiCooldown()` API calls with Bearer auth headers.
  - Confirmed 4 KPI cards, Circuit Breaker banner, and recent logs table render properly.
- **AI Mistakes & Corrections:**
  - *Observed Issue:* TypeScript error `error TS2353: Object literal may only specify known properties, and 'prompt_version' does not exist in type 'AIUsageLogItem'`. AI attempted to add `prompt_version` to local fallback objects conforming to `AIUsageLogItem`.
  - *Commit Hash / File:* `frontend/src/services/api/telemetry.ts` (Commit `e2089ab`)
  - *Fix Applied:* Defined `export interface TelemetryLogItem extends AIUsageLogItem { prompt_version?: string; tools_called?: string[]; }` in `telemetry.ts` to extend the contract without violating the frozen `types.ts` owned by Integrator.

---

## Session 3: RBAC Role Switcher, Ticket Sorting/Pagination/Delete & Multi-Agent Verification Trace (Task C3)
- **Date:** 2026-10-21
- **AI Tool Used:** Antigravity / Gemini 3.5 Flash
- **Key Prompt:** "Implement 1-click RBAC switcher between Admin and User in Header, hide/lock admin tabs when role=user, add sort/pagination/delete in AgentDashboard, and embed 3-agent verification trace in KnowledgeManagerView modal."
- **Manual Verification & Changes:**
  - Verified 1-click role switcher in `LoginSwitcher.tsx`.
  - Tested ticket sorting (`created_at`, `priority`, `status`, `sla_hours`) and client-side pagination.
  - Verified `deleteTicket(ticketId)` triggers `DELETE /api/v1/tickets/{id}` with admin guard.
  - Embedded `VerificationTrace` in `KnowledgeManagerView.tsx`.
- **AI Mistakes & Corrections:**
  - *Observed Issue 1:* Missing comma in multi-line import in `TicketDetail.tsx`: `Inbox \n Trash2` caused `error TS1005: ',' expected`.
  - *Observed Issue 2:* AI hallucinated non-existent Lucide icon `MessageSquareCheck` in `VerificationTrace.tsx` causing `error TS2724: '"lucide-react"' has no exported member named 'MessageSquareCheck'`.
  - *Commit Hash / File:* `frontend/src/features/knowledge/VerificationTrace.tsx` (Commit `1b78353`)
  - *Fix Applied:* Corrected comma in `TicketDetail.tsx` and replaced `MessageSquareCheck` with `MessageSquare`.

---

## Session 4: Capstone Documentation & E2E Validation (Task C4)
- **Date:** 2026-10-21
- **AI Tool Used:** Antigravity / Gemini 3.5 Flash
- **Key Prompt:** "Generate formal 7-chapter project report in docs/REPORT.md, 15-slide outline with 8-min demo script and 10-min live change playbook in docs/PRESENTATION_AND_DEMO.md, and update README.md and docs/PROPOSAL.md with test accounts and team roster."
- **Manual Verification & Changes:**
  - Verified all 7 chapters of `REPORT.md` align with 24-case benchmark metrics (Baseline 33.3% -> Upgraded 100%).
  - Verified 15 slides outline, 8-minute demo step-by-step breakdown, and 4 instructor live change scenarios in `PRESENTATION_AND_DEMO.md`.
  - Verified test accounts table and Data Privacy & PII Masking policy in `README.md`.
  - Executed all 55 Pytest backend tests (100% passed) and verified Vite production build.

---

## Session 5: Cross-Feature Offline Tests & Real AI Failure Audit (Task C5 / REQ-28)
- **Date:** 2026-10-22
- **AI Tool Used:** Antigravity / Claude 3.7 Sonnet & Gemini 3.5 Flash
- **Key Prompt:** "Write offline cross-feature integration tests in backend/tests/common/ covering the full customer journey: login -> list tickets -> submit ticket form -> chat assistant -> tool call escalation -> two-phase action confirmation, using existing conftest fixtures."
- **Manual Verification & Changes:**
  - Implemented `test_cross_feature_flows.py` with 4 comprehensive test scenarios:
    1. `test_customer_flow_login_list_create_chat_confirm`: Validates complete customer flow with real JWT token, ticket form submission, chat assistance, mutating action confirmation, and agent queue reflection.
    2. `test_cancelled_confirmation_does_not_create_ticket`: Verifies two-phase cancel logic.
    3. `test_customer_cannot_use_agent_only_routes_after_login`: Verifies RBAC data/route isolation (403 Forbidden).
    4. `test_protected_flow_rejects_missing_token`: Verifies 401 Unauthorized barrier.
  - Executed `python -m pytest backend/tests/test_api.py backend/tests/common -v` -> 14 passed in 3.91s.
- **Audited Real AI Failures in Codebase (Evidence & Fix Commits):**
  1. *Real Failure 1 (Auth Bypass & Unverified JWT):*
     - *Observed Issue:* In the initial AI-generated auth implementation (`app/api/v1/endpoints/auth.py`), password validation was completely bypassed—any password was accepted for any seeded user! In addition, Google OAuth credential decoding turned off signature verification (`options={"verify_signature": False}`), allowing arbitrary token forgery.
     - *Why It Happened:* The AI assistant prioritized "making tests pass quickly without external Google network dependencies" by omitting cryptographic signature checks.
     - *Commit Hash & Author:* Fixed by Dev B (`@BapVitHoang`) in commit `eef0af827d1904bf24d86c0cbfbc6508cc04a290` (`feat(auth): implement real JWT auth, bcrypt hashing, and RBAC endpoint guards`).
     - *Fix Applied:* Enforced bcrypt password hashing verification via `passlib`, real HS256 JWT tokens with expiry, and secure token validation.
  2. *Real Failure 2 (Gemini Live Call HTTP 400 Client Error):*
     - *Observed Issue:* Live Gemini API calls returned `HTTP 400 Bad Request` during structured output extraction because the AI assistant generated unsupported request parameters for the GenAI SDK client.
     - *Why It Happened:* The assistant mixed parameter conventions between the deprecated `google-generativeai` SDK and the new `google-genai` SDK (`GenerateContentConfig`), passing incompatible parameter structures.
     - *Commit Hash & Author:* Fixed by Dev A (`@TheOrijinnn`) in commits `192fecc` and `afbb08d`.
     - *Fix Applied:* Re-aligned request payload configuration to match Google GenAI SDK v1beta specifications and added fail-safe fallbacks.

---

## Session 6: CR-DEVC-01 & CR-DEVC-02 Authenticated Tickets & Pagination (Change Requests)
- **Date:** 2026-10-25
- **AI Tool Used:** Antigravity / Gemini 3.8 Flash
- **Key Prompt:** "In createTicket(), attach getAuthHeaders() to headers to support authenticated ticket creation (POST /api/v1/tickets now requires Bearer auth per REQ-SEC-03) and prompt unauthenticated visitors to log in. In getTickets(), support pagination (?page=2) and sorting with 43 seeded tickets in Docker PostgreSQL."
- **Manual Verification & Changes:**
  - Attached `getAuthHeaders({ 'Content-Type': 'application/json' })` to `POST /api/v1/tickets` in `frontend/src/services/api/tickets.ts`.
  - Added pre-check and unauthenticated visitor prompt in `frontend/src/components/TicketFormView.tsx` with warning banner and toast notification.
  - Added `page?: number` filter, calculated `skip`, and default `limit: 50` in `getTickets()` to fetch all 43 seeded tickets for Admin while respecting RBAC isolation for An Nguyen.
  - Verified `npm run lint` and `npm run build` completed with zero errors.
- **AI Mistakes & Corrections:**
  - *Observed Issue:* In `createTicket`, calling `toastFn` for 401 was initially overridden by the generic `catch (err)` block in `TicketFormView.tsx` displaying "Không thể tạo ticket. Vui lòng kiểm tra kết nối!".
  - *Commit Hash / File:* `frontend/src/components/TicketFormView.tsx`
  - *Fix Applied:* Updated `handleSubmit` in `TicketFormView.tsx` to handle `err.statusCode === 401` gracefully without displaying the generic network error message, and pre-checked `getAuthToken()` before invoking submission.
