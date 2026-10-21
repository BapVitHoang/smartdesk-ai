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
