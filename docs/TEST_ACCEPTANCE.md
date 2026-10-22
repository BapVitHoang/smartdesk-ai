# SmartDesk AI - Test Suite & Acceptance Test Matrix

> **Document:** Enterprise Test Evidence & Quality Assurance Matrix  
> **Target:** Verification of complete customer support workflow, RAG, fallback, ticket triage, agent copilot, multi-domain workspaces, and active verification.

---

## 1. Automated Test Suite (Pytest + HTTPX AsyncClient)

SmartDesk AI includes automated integration and unit tests located under `backend/tests/`.

### Running Automated Tests
```bash
pytest backend/tests/ -v
```

### Automated Test Coverage Summary

| Test Case Name | Target Endpoint / Module | Description | Verification Assertion |
| :--- | :--- | :--- | :--- |
| `test_health_check` | `GET /api/v1/health` | Readiness probe and database ping | Status 200, DB `connected`, version `1.0.0` |
| `test_smoke_test` | `GET /api/v1/health/smoke-test` | Round-trip latency benchmark | Status 200, `latency_ms` measured, `status: PASS` |
| `test_chat_rag_and_fallback` | `POST /api/v1/chat` | Customer RAG query with citations | Status 200, citations list, latency < 4000ms |
| `test_chat_prompt_injection_guardrail` | `POST /api/v1/chat` | Security prompt injection filter | Status 400, `PROMPT_SECURITY_VIOLATION` |
| `test_create_ticket_with_copilot_triage` | `POST /api/v1/tickets` | Ticket creation & SLA estimation | Status 201, `#TICK-XXXX` format, `ai_tags`, `ai_draft_reply` |
| `test_list_and_filter_tickets` | `GET /api/v1/tickets` | Dashboard ticket filtering | Status 200, list matches category/priority |
| `test_update_ticket_and_customize_draft`| `PATCH /api/v1/tickets/{id}` | Support agent edits draft reply | Status 200, draft reply and status updated |
| `test_agent_copilot_regenerate_draft` | `POST /api/v1/agent/tickets/{id}/generate-draft` | AI Copilot draft regeneration | Status 200, new personalized draft synthesized |
| `test_create_and_list_workspaces` | `GET/POST /api/v1/workspaces` | Multi-domain workspace listing and creation | Status 200/201, tenant isolation and persona configuration |
| `test_document_upload_and_chunking` | `POST /workspaces/{id}/documents/upload` | File ingestion (.txt, .md, .pdf), chunking & embedding | Status 201, chunks stored, document status `pending` |
| `test_document_verification_pipeline` | `POST /documents/{id}/verify` | Active AI verification: Synthetic QA $\to$ Self-Test $\to$ AI Judge | Status 200, faithfulness score, detailed verification report |
| `test_document_publish_and_rag_isolation` | `POST /documents/{id}/publish` | Publishing verified doc & isolated RAG retrieval | Status 200, chunk status `published`, RAG search scoped to workspace |
| `test_cost_guard_circuit_breaker_on_429` | Internal / Service | Free Tier Rate Limit Circuit Breaker (HTTP 429) | 60s cooldown lock, deterministic unit pseudo-vector fallback |
| `test_ollama_provider_*` | `llm_service` / `embedding_service` | Dual-mode Ollama (`qwen2.5:3b` & `nomic-embed-text`) | Local LLM generation, 768-dim embedding, fallback resilience |
| `test_customer_flow_login_list_create_chat_confirm` | E2E Cross-Feature Flow | Login $\to$ list tickets $\to$ form creation $\to$ chat escalation $\to$ confirm | Status 200/201, real JWT token, ticket `#TICK-XXXX` visible in agent queue |
| `test_cancelled_confirmation_does_not_create_ticket`| E2E Action Cancel | Two-phase pending action cancellation in chat | Status 200, `executed: false`, ticket count unchanged |
| `test_customer_cannot_use_agent_only_routes_after_login`| RBAC Data & Route Guard | Customer attempted access to admin telemetry / delete | Status 403 Forbidden |
| `test_auth_security_*` | Auth Security Module | Google token signature verification, scrypt password hashing & 429 throttle | Status 401 on forged/wrong password, status 429 after 10 attempts |

---

## 2. Documented Manual Acceptance Tests (7 Core Scenarios)

### Scenario 1: Customer RAG Inquiry with Grounded Citations
- **Objective:** Verify that customer questions receive accurate, grounded responses with verifiable citation links.
- **Preconditions:** Frontend running at `http://localhost:3000`, Backend running at `http://localhost:8000`.
- **Step-by-step Actions:**
  1. Open the **Customer AI Chat** tab (`/chat`).
  2. Click the quick prompt pill: *"Password Reset"*, or type *"How do I reset my password if I lost access to my email?"*
  3. Click **Send** (`Enter`).
- **Expected Results:**
  - Assistant responds within 2 seconds.
  - Response outlines step-by-step instructions (checking email, backup phone, recovery key).
  - A structured Citation Badge appears: `[doc-01: How to Reset Your CloudDesk / SmartDesk Password]`.
  - User can click the citation link to view the knowledge reference.

---

### Scenario 2: Circuit Breaker & Non-AI Deterministic Fallback Trigger
- **Objective:** Verify User Story 2 (Circuit Breaker) when external LLM times out or encounters network failure.
- **Preconditions:** Server running in fallback mode or with invalid API key.
- **Step-by-step Actions:**
  1. In the top navigation bar, toggle the Demo State controller to **Error / Fallback** mode (or send a query with LLM disabled).
  2. Send query: *"What are the API rate limits for the Starter plan?"*
- **Expected Results:**
  - The system catches the error within the 4.0s budget without crashing.
  - Response is served from `FallbackService` (BM25 Matcher on `seed_faq.json`).
  - Response displays: *"We could not reach the real-time AI assistant. Based on our verified Knowledge Base, here is the relevant article: 'API Rate Limits, HTTP 429 Errors, and Exponential Backoff'"*.
  - An amber banner appears recommending ticket escalation: **[Escalate to Priority Ticket]**.

---

### Scenario 3: Submit Support Ticket with Client-Side & Server Validation
- **Objective:** Verify customer ticket submission, field validation, and automated ticket code generation.
- **Preconditions:** Navigate to **Submit Ticket** tab (`/ticket`).
- **Step-by-step Actions:**
  1. Leave fields empty and click **Submit Ticket**. Observe red error borders on required fields.
  2. Fill valid data:
     - **Full Name:** `Nguyen Van A`
     - **Customer Email:** `nguyenvana@example.com`
     - **Category:** `Authentication`
     - **Priority:** `Urgent`
     - **Subject:** `Lost 2FA recovery token for corporate account`
     - **Description:** `I changed my mobile device and lost access to the authenticator app. Need help resetting.`
  3. Click **Submit Ticket**.
- **Expected Results:**
  - Submission spinner displays for ~800ms.
  - Success modal/card appears displaying newly generated Ticket ID: `#TICK-1001` (or `#TICK-XXXX`).
  - SLA indicates estimated response within **2 hours** (for Urgent).
  - Button **[View in Agent Queue]** allows immediate navigation to the Agent Triage Dashboard.

---

### Scenario 4: Support Agent Triage Dashboard & AI Copilot Draft Customization
- **Objective:** Verify agent queue management, filtering, and AI draft reply editing.
- **Preconditions:** Navigate to **Agent Triage** tab (`/agent`).
- **Step-by-step Actions:**
  1. In the left panel, select the newly created ticket `#TICK-1001`.
  2. Inspect the **AI Tags** displayed on the card: `[Authentication]`, `[Urgent]`, `[2FA Recovery]`.
  3. In the right panel, observe the pre-drafted response in the **AI Suggested Draft** box.
  4. Edit the text in the textarea: add a custom greeting or verification instructions.
  5. Click **[Approve & Send Reply]**.
- **Expected Results:**
  - Ticket status transitions to `Resolved` (or `In Progress`).
  - Success toast notification confirms: *"Draft approved and reply dispatched to customer"*.
  - Ticket counter in the header updates dynamically.

---

### Scenario 5: Dynamic Knowledge Ingestion & Active AI Verification Engine
- **Objective:** Verify document upload, text extraction, chunking, and the 3-stage AI Verification Engine before publishing to production RAG.
- **Preconditions:** Navigate to **4. Quản lý Tri thức & Sát hạch** tab (`/knowledge`).
- **Step-by-step Actions:**
  1. Select Workspace **"Nha Khoa SmileCare"** from the workspace dropdown.
  2. In the upload card, upload file `backend/data/sample_documents/nha_khoa_smilecare_bang_gia_dich_vu.txt`.
  3. Verify the document appears in the table with status badge **"Chờ sát hạch (Pending)"**.
  4. Click button **"Xem Chunks"** to inspect extracted chunks (700 chars, 100 overlap).
  5. Click button **"Sát hạch AI (Verify)"**. Wait for the 3-stage verification pipeline to complete (Synthetic QA generation $\to$ RAG self-test retrieval $\to$ AI Judge faithfulness evaluation).
  6. In the Verification Studio modal, review the Faithfulness Score (e.g. 100% or $\ge 85\%$), question-answer audit cards, and citations.
  7. Click **"Phê duyệt & Xuất bản vào RAG (Publish)"**.
- **Expected Results:**
  - Document status updates to **"Đã xuất bản (Published)"** with green badge.
  - Document chunks are now active and indexed for retrieval in Nha Khoa SmileCare workspace.

---

### Scenario 6: Multi-Domain Workspace Context Isolation in Chat & Tickets
- **Objective:** Verify that RAG retrieval, system persona, and ticket routing are completely isolated per tenant workspace.
- **Preconditions:** Documents published in both Default, SmileCare, and TechStore workspaces.
- **Step-by-step Actions:**
  1. Go to **1. AI Trợ lý Khách hàng** tab (`/chat`).
  2. Switch workspace dropdown to **"Nha Khoa SmileCare"**. Observe persona badge showing: *"Nha Khoa SmileCare - Thân thiện, ân cần, giải thích cặn kẽ"*.
  3. Ask: *"Chi phí tẩy trắng răng tại phòng khám là bao nhiêu?"*
  4. Observe response: Correctly answers 1.800.000 VNĐ with SmileCare tone and citation badge.
  5. Switch workspace dropdown to **"Điện Máy TechStore"**.
  6. Ask: *"Chính sách đổi trả sản phẩm lỗi trong bao nhiêu ngày?"*
  7. Observe response: Correctly answers 30 ngày (1 đổi 1) with TechStore electronics persona and citation badge.
  8. Click **"Gửi Ticket Hỗ trợ"** from chat: the ticket form pre-selects the corresponding workspace tenant automatically.
- **Expected Results:**
  - Cross-domain leakage is strictly 0%. Queries in SmileCare cannot access TechStore policies and vice versa.
  - Persona and business rules correctly govern the bot's tone and advice.

---

### Scenario 7: Free Tier Rate Limit Circuit Breaker (HTTP 429 Guard)
- **Objective:** Verify system resilience when Google Gemini Free Tier rate limits (15 RPM / 429 Too Many Requests) are exceeded.
- **Preconditions:** Rapid query generation or triggered 429 response.
- **Step-by-step Actions:**
  1. Trigger consecutive requests or simulate Gemini 429 ResourceExhausted exception.
  2. Check backend logging and frontend UI response.
- **Expected Results:**
  - Cost-Guard Circuit Breaker catches HTTP 429, sets `cooldown_until = now + 60s`.
  - Subsequent requests within the 60s cooldown immediately bypass remote Gemini API without hanging or failing.
  - Embeddings fallback smoothly to deterministic hash-based 768-dim unit vectors; chat falls back to local BM25 knowledge search.
  - Frontend receives response with `is_fallback: true` and displays friendly notification: *"Hệ thống AI đang tạm nghỉ để tối ưu hạn mức (Free Tier Cooldown). Đang chuyển sang chế độ đối soát tri thức cục bộ."*
  - Zero crashes, zero unhandled 500 errors.

---

## 3. Visual & Responsive UI Acceptance Matrix (REQ-31, REQ-33, REQ-34)

To guarantee compliance with responsive viewport requirements (`REQ-34`), search/filter/sort/pagination (`REQ-31`), and admin telemetry observability (`REQ-33`), the application was verified across both **Desktop (`1440x900`)** and **Mobile (`375x812` - iPhone standard)** viewports using automated headless Edge / Playwright sessions.

### 3.1 Visual Verification Results & Evidence Artifacts

| Feature / UI View | Viewport | Verified Interactive Element | Evidence Artifact Path | Result |
| :--- | :---: | :--- | :--- | :---: |
| **Customer AI Chat** | `1440x900` | Real-time SSE streaming bubble, quick prompt pills, clickable citation badges | [`docs/evidence/chat-desktop-1440x900.png`](./evidence/chat-desktop-1440x900.png) | **PASS** |
| **Two-Phase Action Card** | `1440x900` | Two-phase pending mutating tool card (`create_escalation_ticket`) with [Xác nhận thực thi] and [Hủy bỏ] buttons | [`docs/evidence/chat-tool-confirmation-card.png`](./evidence/chat-tool-confirmation-card.png) | **PASS** |
| **Customer AI Chat (Mobile)** | `375x812` | Touch-friendly chat message stream, responsive bottom input bar, full mobile visibility | [`docs/evidence/chat-mobile-375x812.png`](./evidence/chat-mobile-375x812.png) | **PASS** |
| **Ticket Submission Form** | `1440x900` | Multi-field validation, category selector, SLA response hours live estimation card | [`docs/evidence/ticket-form-desktop.png`](./evidence/ticket-form-desktop.png) | **PASS** |
| **Ticket Submission Form (Mobile)** | `375x812` | Full-width mobile input controls, sticky navigation hamburger menu toggle | [`docs/evidence/ticket-form-mobile.png`](./evidence/ticket-form-mobile.png) | **PASS** |
| **Agent Triage Dashboard** | `1440x900` | Sorting dropdown (`created_at`, `priority`, `status`, `sla_hours`), pagination controls, AI draft reply inspection | [`docs/evidence/agent-dashboard-desktop-1440x900.png`](./evidence/agent-dashboard-desktop-1440x900.png) | **PASS** |
| **Ticket Delete Action** | `1440x900` | Confirmation modal before permanent deletion (`DELETE /api/v1/tickets/{id}` with admin guard) | [`docs/evidence/agent-ticket-delete-confirm.png`](./evidence/agent-ticket-delete-confirm.png) | **PASS** |
| **Agent Dashboard (Mobile)** | `375x812` | Split-pane flexbox fix (`h-1/2 md:h-full`): ticket queue and ticket detail both scrollable independently | [`docs/evidence/agent-dashboard-mobile-375x812.png`](./evidence/agent-dashboard-mobile-375x812.png) | **PASS** |
| **Admin AI Telemetry Panel** | `1440x900` | 4 KPI cards (Total AI Calls, Cost USD, Avg Latency, Fallback/Refused), Cost-Guard Circuit Breaker banner, 1-click [Mở Khóa Cooldown 429] button, recent request audit logs | [`docs/evidence/telemetry-panel-desktop.png`](./evidence/telemetry-panel-desktop.png) | **PASS** |
| **Admin Telemetry (Mobile)** | `375x812` | Vertically stacked KPI metric cards, scrollable telemetry log table on mobile screen | [`docs/evidence/telemetry-panel-mobile.png`](./evidence/telemetry-panel-mobile.png) | **PASS** |
| **Knowledge Manager Studio** | `1440x900` | Multi-domain tenant workspace switcher (Default, SmileCare, TechStore), document upload area, chunk viewer | [`docs/evidence/knowledge-manager-desktop.png`](./evidence/knowledge-manager-desktop.png) | **PASS** |
| **Active Verification Studio Modal** | `1440x900` | 3-Agent Hand-off Trace (`SyntheticQAExamAgent` $\to$ `SandboxRAGAgent` $\to$ `FaithfulnessJudgeAgent`), Faithfulness Score, audit questions | [`docs/evidence/knowledge-verification-trace-modal.png`](./evidence/knowledge-verification-trace-modal.png) | **PASS** |
| **RBAC Role-Based Access Barrier** | `1440x900` | 1-Click Role Switcher toggling to `an.nguyen@company.vn`: Tab 3 (Agent Dashboard) & Tab 4 (Knowledge) locked with Lock icon and 'Admin' badge | [`docs/evidence/rbac-user-mode-locked.png`](./evidence/rbac-user-mode-locked.png) | **PASS** |

### 3.2 Error Toast & Fallback Localization Policy
- **Vietnamese Language Standard:** All customer-facing and agent-facing toast alerts, error banners, and modal prompts are strictly rendered in Vietnamese (e.g., *"Đã chuyển sang vai trò QUẢN TRỊ VIÊN (Admin)"*, *"Lỗi xác thực: Vui lòng đăng nhập lại"*, *"Hệ thống AI đang tạm nghỉ để tối ưu hạn mức (Free Tier Cooldown)"*).
- **Zero Fake Success Policy:** When backend API calls return HTTP 4xx or 5xx (e.g. `PROMPT_SECURITY_VIOLATION`, `401 Unauthorized`, `403 Forbidden`), the frontend NEVER fabricates a fake successful result in local state; instead, an error toast is surfaced with the exact server message.
