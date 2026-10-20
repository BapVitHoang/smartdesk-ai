# SmartDesk AI - Test Suite & Acceptance Test Matrix

> **Document:** Enterprise Test Evidence & Quality Assurance Matrix  
> **Target:** Verification of complete customer support workflow, RAG, fallback, ticket triage, and agent copilot.

---

## 1. Automated Test Suite (Pytest + HTTPX AsyncClient)

SmartDesk AI includes automated integration and unit tests located in `backend/tests/test_api.py`.

### Running Automated Tests
```bash
cd backend
pytest tests/ -v
```

### Automated Test Coverage Summary

| Test Case Name | Target Endpoint | Description | Verification Assertion |
| :--- | :--- | :--- | :--- |
| `test_health_check` | `GET /api/v1/health` | Readiness probe and database ping | Status 200, DB `connected`, version `1.0.0` |
| `test_smoke_test` | `GET /api/v1/health/smoke-test` | Round-trip latency benchmark | Status 200, `latency_ms` measured, `status: PASS` |
| `test_chat_rag_and_fallback` | `POST /api/v1/chat` | Customer RAG query with citations | Status 200, citations list, latency < 4000ms |
| `test_chat_prompt_injection_guardrail` | `POST /api/v1/chat` | Security prompt injection filter | Status 400, `PROMPT_SECURITY_VIOLATION` |
| `test_create_ticket_with_copilot_triage` | `POST /api/v1/tickets` | Ticket creation & SLA estimation | Status 201, `#TICK-XXXX` format, `ai_tags`, `ai_draft_reply` |
| `test_list_and_filter_tickets` | `GET /api/v1/tickets` | Dashboard ticket filtering | Status 200, list matches category/priority |
| `test_update_ticket_and_customize_draft`| `PATCH /api/v1/tickets/{id}` | Support agent edits draft reply | Status 200, draft reply and status updated |
| `test_agent_copilot_regenerate_draft` | `POST /api/v1/agent/tickets/{id}/generate-draft` | AI Copilot draft regeneration | Status 200, new personalized draft synthesized |
| `test_workspaces_crud` | `GET/POST /api/v1/workspaces` | Multi-domain workspace listing and creation | Status 200/201, tenant isolation and persona configuration |
| `test_document_upload_and_chunking` | `POST /workspaces/{id}/documents/upload` | File ingestion (.txt, .md, .pdf), chunking & embedding | Status 201, chunks stored, document status `pending` |
| `test_document_verification_pipeline` | `POST /documents/{id}/verify` | Active AI verification: Synthetic QA $\to$ Self-Test $\to$ AI Judge | Status 200, faithfulness score, detailed verification report |
| `test_document_publish_and_rag_isolation` | `POST /documents/{id}/publish` | Publishing verified doc & isolated RAG retrieval | Status 200, chunk status `published`, RAG search scoped to workspace |
| `test_circuit_breaker_free_tier` | Internal / Service | Free Tier Rate Limit Circuit Breaker (HTTP 429) | 60s cooldown lock, deterministic unit pseudo-vector fallback |

---

## 2. Documented Manual Acceptance Tests (7 Scenarios)

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

## 2. Documented Manual Acceptance Tests (4 Scenarios)

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
