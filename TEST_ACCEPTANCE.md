# SmartDesk AI - Test Suite & Acceptance Test Matrix

> **Deliverable:** Homework 3B Test Evidence & Verification Document  
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
