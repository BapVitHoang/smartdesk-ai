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

## 2. Decision Log
- Date: 2026-10-20 — Switched mobile split-pane flexbox from `h-full` to `h-1/2 md:h-full` in `AgentDashboardView.tsx` to fix mobile scrolling.
- Date: 2026-10-21 — Integrated SSE token streaming and Two-Phase Agent Confirmation Card in `ChatView.tsx`.
