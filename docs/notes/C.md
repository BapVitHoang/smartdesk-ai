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

### Task C3: OAuth2 Role Switcher, Ticket Sorting/Pagination/Delete & Multi-Agent Verification Trace (`TASK-12`, `TASK-13`, `TASK-08` UI / `REQ-09`, `REQ-17`, `REQ-30`, `REQ-31`, `REQ-34`)
1. **Authentication & RBAC Navigation (`LoginSwitcher.tsx`, `Header.tsx`, `App.tsx`):**
   - Upgraded `LoginSwitcher.tsx` with a 1-click toggle button to quickly switch between `admin@smartdesk.ai` (Admin) and `an.nguyen@company.vn` (User).
   - In `Header.tsx`, locked/hid Tab 3 (*Agent Triage Dashboard*) and Tab 4 (*Quản lý Tri thức*) when role is `user` to visually communicate RBAC permissions.
   - In `App.tsx`, added role guard: switching to `user` role automatically navigates back to Tab 1 (*Customer AI Chatbot*).
2. **Ticket Sorting, Pagination & Deletion (`TicketToolbar.tsx`, `TicketDetail.tsx`, `AgentDashboardView.tsx`):**
   - Enhanced `TicketToolbar.tsx` with sorting dropdown (`created_at` Mới nhất, `priority` Mức ưu tiên, `status` Trạng thái, `sla_hours` Cam kết SLA).
   - Added client/server-side pagination (`currentPage`, `totalPages`, previous/next controls) in `AgentDashboardView.tsx`.
   - Added Ticket Delete capability (`DELETE /api/v1/tickets/{id}`) with confirmation prompt and live state updates in `TicketDetail.tsx` and `services/api/tickets.ts`.
   - Maintained mobile flexbox responsiveness (`h-1/2 md:h-full`) to guarantee full visibility on screens < 768px.
3. **Multi-Agent Verification Trace (`VerificationTrace.tsx`, `KnowledgeManagerView.tsx`):**
   - Enhanced `VerificationTrace.tsx` to visualize the 3-agent verification workflow:
     - **Fact Checker Agent**: checks factual consistency with ground-truth chunks.
     - **Completeness Auditor Agent**: verifies complete coverage of instructions & caveats.
     - **Tone & Policy Checker Agent**: verifies professional customer support tone & policy adherence.
   - Embedded `<VerificationTrace report={activeReport} />` directly into the Active Knowledge Verification report modal of `KnowledgeManagerView.tsx`.
4. **Verification & Build:**
   - Passed TypeScript typecheck (`npm run lint` -> `tsc --noEmit`).
   - Passed production build (`npm run build` -> `vite build`).

---

### Task C4: Capstone Final Documentation, Presentation & Playbook (`TASK-16`, `TASK-17` / `REQ-24..29`, `REQ-37`, `REQ-39..42`)
1. **Comprehensive Project Report (`docs/REPORT.md`):**
   - Authored formal 7-chapter project report (~15 pages) aligned with course specifications:
     - Chương 1: Giới thiệu bài toán, đối tượng người dùng & phạm vi hệ thống.
     - Chương 2: 12 User Stories (`US-01..US-12`) & Bảng Requirement Traceability Matrix đầy đủ.
     - Chương 3: Kiến trúc hệ thống (Sơ đồ Mermaid thực tế) & 4 Architecture Decision Records (`ADR-001..004`).
     - Chương 4: Thiết kế AI chuyên sâu (Dual Provider Gemini 3.5 Flash Lite & Ollama Qwen2.5, Quản lý Prompt `prompts.json`, 4 Agent Tools có xác nhận, Pydantic Structured Output, 3-Agent Verification Studio).
     - Chương 5: Bảo mật, Hàng rào chắn (Guardrails EN/VI), Quyền riêng tư (PII Redaction `redact_pii`) & Cơ chế dự phòng BM25 Circuit Breaker.
     - Chương 6: Kết quả thực nghiệm bộ 24 Test Cases (Baseline 33.3% -> Upgraded 100.0%), phân tích chi phí Token & độ trễ.
     - Chương 7: Hạn chế hiện tại & Hướng phát triển.
2. **Slide Outline, 8-min Demo Script & Live Change Playbook (`docs/PRESENTATION_AND_DEMO.md`):**
   - 15 Slides structured outline for project defense.
   - 8-minute minute-by-minute live demo script (RAG grounded answers, 2-phase confirmation card, live Vietnamese prompt injection blocking, agent copilot triage, active verification studio, telemetry cooldown reset).
   - 10-minute Live Change Playbook with 4 concrete instructor modification scenarios (`prompts.json` rule addition, `config.py` chunk size update, `TicketCopilotStructuredOutput` schema extension, `agent_tools.py` new tool creation).
3. **Repository Readme & Proposal Updates (`README.md`, `docs/PROPOSAL.md`):**
   - Added Test Accounts table (`admin@smartdesk.ai` and `an.nguyen@company.vn`).
   - Added Data Privacy & PII Masking Policy section in `README.md`.
   - Updated team member roster with Full Names, Student IDs (MSSV), and GitHub accounts in `docs/PROPOSAL.md`.
4. **Verification:**
   - 55/55 backend pytest test cases passed.
   - Frontend `npm run lint` and `npm run build` passed cleanly.

---

## 2. Decision Log
- Date: 2026-10-20 — Switched mobile split-pane flexbox from `h-full` to `h-1/2 md:h-full` in `AgentDashboardView.tsx` to fix mobile scrolling.
- Date: 2026-10-21 — Integrated SSE token streaming and Two-Phase Agent Confirmation Card in `ChatView.tsx`.
- Date: 2026-10-21 — Embedded AI Telemetry & Cost-Guard Cooldown reset panel in `AgentDashboardView.tsx`.
- Date: 2026-10-21 — Implemented 1-click RBAC switcher, ticket sorting, pagination, delete, and 3-agent verification trace.
- Date: 2026-10-21 — Created comprehensive Capstone documentation suite (`REPORT.md`, `PRESENTATION_AND_DEMO.md`, `C-ai-usage.md`).
- Date: 2026-10-25 — Implemented CR-DEVC-01: Attached `getAuthHeaders()` to `createTicket()` per REQ-SEC-03, added unauthenticated visitor warning banner & toast prompt in `TicketFormView.tsx`.
- Date: 2026-10-25 — Implemented CR-DEVC-02: Added `page` query param & default `limit: 50` to `getTickets()` supporting Docker PostgreSQL 43 seeded tickets and RBAC tenant isolation (Admin sees 43, An Nguyen sees isolated tickets).
