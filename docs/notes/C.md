# Developer C — Technical Notes & Decisions

> Workstream: Frontend UX, QA & Documentation (`feature/c-frontend-docs`)  
> Owner: Developer C

## 1. Ongoing Implementation Notes

### Task C1: SSE Token Streaming UI & Confirmation Card (`TASK-11` UI / `REQ-04`, `REQ-10`, `REQ-14`)
1. **API Client Updates (`frontend/src/services/api/chat.ts`):**
   - Enhanced `streamChatMessage()` and `sendChatMessage()` to receive and parse `pending_action` and `tools_called` fields from backend payloads (SSE events: `metadata`, `token`, `done`).
   - Implemented `confirmChatAction(actionId: string, confirmed: boolean)` calling `POST /api/v1/chat/confirm-action` with auth headers.
2. **Chat Interface Enhancements (`frontend/src/components/ChatView.tsx`):**
   - Switched message sending to `streamChatMessage()`: Tokens render in real time as they arrive from SSE with an inline pulsing cursor (`animate-pulse`).
   - Rendered violet badges (`bg-violet-50 text-violet-700`) displaying any AI tools called (`tools_called`).
   - Implemented interactive Vietnamese **Two-Phase Confirmation Card** for mutating agent actions (`create_escalation_ticket`, `update_ticket_priority_or_status`), featuring **[Xác nhận thực thi]** (`bg-indigo-600`) and **[Hủy bỏ]** buttons with loading feedback and execution result feedback.
3. **Verification & Build:**
   - Passed TypeScript typecheck (`npm run lint` -> `tsc --noEmit`).
   - Passed production build (`npm run build` -> `vite build`).

---

### Task C2: Admin AI Telemetry & Cost-Guard Panel (`TASK-10` UI / `REQ-22`, `REQ-33`)
1. **API Client Updates (`frontend/src/services/api/telemetry.ts`):**
   - Corrected endpoint URL in `getAiUsageSummary()` from `/admin/ai-usage/summary` to `${API_BASE_URL}/agent/ai-usage?limit=...` with Bearer auth headers via `getAuthHeaders()`.
   - Implemented `resetAiCooldown(): Promise<ResetCooldownResponse>` calling `POST ${API_BASE_URL}/agent/ai-usage/reset-cooldown` with admin auth headers.
   - Preserved graceful offline fallback data for offline development/mock mode.
2. **Telemetry Panel Component (`frontend/src/features/telemetry/TelemetryPanel.tsx`):**
   - Rendered 4 core KPI cards:
     - **Tổng Lượt Yêu Cầu AI** (`total_requests` with success/error split).
     - **Chi Phí & Token** (`total_cost_usd` formatted to 4 decimals, total/input/output tokens).
     - **Độ Trễ Trung Bình** (`avg_latency_ms` with target SLA < 1,500ms indicator).
     - **Dự Phòng / Từ Chối** (`fallback_count` for BM25 fallback, `refused_count` for prompt guardrails).
   - Added Cost-Guard Circuit Breaker alert banner:
     - When `cooldown_active == true`: Displays amber warning banner with HTTP 429 notification and prominent **"Mở Khóa Cooldown 429"** button calling `resetAiCooldown()`.
     - When `cooldown_active == false`: Displays green readiness banner confirming Cloud Gemini is operating normally.
   - Rendered Model Distribution breakdown badges (`gemini-3.5-flash-lite`, `seed_faq_bm25`, etc.).
   - Rendered Audit & Telemetry table displaying recent logs with timestamp, endpoint, model/version, tools called badges, token counts, latency, cost in USD, and status badges (`success`, `fallback`, `refused`).
3. **Dashboard Integration (`frontend/src/components/AgentDashboardView.tsx`):**
   - Added sub-navigation toggle buttons: **"Hàng đợi Ticket"** (with live count badge) vs. **"Giám sát AI & Chi phí (Telemetry)"** (with Cost-Guard badge).
   - Embedded `TelemetryPanel` seamlessly when telemetry view is selected.
4. **Verification & Build:**
   - Passed TypeScript typecheck (`npm run lint` -> `tsc --noEmit`).
   - Passed production build (`npm run build` -> `vite build`).

---

## 2. Decision Log
- Date: 2026-10-20 — Switched mobile split-pane flexbox from `h-full` to `h-1/2 md:h-full` in `AgentDashboardView.tsx` to fix mobile scrolling.
- Date: 2026-10-21 — Integrated SSE token streaming and Two-Phase Agent Confirmation Card in `ChatView.tsx`.
- Date: 2026-10-21 — Embedded AI Telemetry & Cost-Guard Cooldown reset panel in `AgentDashboardView.tsx`.
