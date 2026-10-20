# SmartDesk AI - Formal API Specifications & Contract (v1)

> **Specification Version:** 1.1.0 (Frozen Contract)  
> **Base URL:** `http://localhost:8000/api/v1`  
> **Architecture Status:** Full Enterprise System Integration (React 19 Vite SPA & FastAPI Async Backend)

---

## 0. Canonical Domain Enums, SLA Rules & Standard Error Format

### 0.1 Ticket Categories (Canonical & Aliases)
- **Canonical Categories (`TicketCategory`):**
  - `"Authentication"` — Login, 2FA, SSO, password recovery.
  - `"Billing"` — Invoices, subscriptions, refunds, payment gateways.
  - `"Bug Report"` — System errors, crashes, API timeouts, defects.
  - `"Feature Request"` — Product enhancements, roadmap suggestions.
  - `"General"` — General inquiries and uncategorized support requests.
- **Accepted Alias:** `"Technical Bug"` is accepted by the backend for backward compatibility and maps to `"Bug Report"`.

### 0.2 Priority Levels & Canonical SLA Hours
| Priority Level | Canonical Value | Target SLA (`estimated_response_hours`) |
| :--- | :--- | :--- |
| Urgent / Critical | `"Urgent"` | **2 hours** |
| High Priority | `"High"` | **4 hours** |
| Medium / Normal | `"Medium"` | **8 hours** |
| Low Priority | `"Low"` | **24 hours** |

### 0.3 Ticket Status Lifecycle Mapping
| Lifecycle Phase | Backend Status (`TicketStatus`) | Frontend UI Status (`Ticket['status']`) |
| :--- | :--- | :--- |
| Initial Submission | `"open"` | `"Open"` |
| Under Review / Triaged | `"in_progress"` | `"Pending"` |
| Solved & Approved | `"resolved"` | `"Resolved"` |

### 0.4 Standardized Error Response Schema (RFC 7807 Style)
All HTTP 4xx and 5xx errors return a consistent JSON structure:
```json
{
  "detail": "Human-readable explanation of the error",
  "error_code": "MACHINE_READABLE_CODE",
  "status_code": 400,
  "details": {}
}
```
Canonical `error_code` values:
- `PROMPT_SECURITY_VIOLATION` (HTTP 400): Prompt injection or security guardrail triggered.
- `VALIDATION_ERROR` (HTTP 422 / 400): Request body or query parameter failed validation.
- `TICKET_NOT_FOUND` / `RESOURCE_NOT_FOUND` (HTTP 404): Requested entity does not exist.
- `UNAUTHORIZED` / `FORBIDDEN` (HTTP 401 / 403): Missing or insufficient authentication/role permissions.
- `INTERNAL_SERVER_ERROR` (HTTP 500): Unexpected server error (sanitized, never leaks stack traces).

---

## 1. Chat & RAG Assistant

### `POST /api/v1/chat`
Ask questions to the customer support AI assistant with verified citation grounding and automatic fallback.

#### Request Headers
- `Content-Type: application/json`

#### Request Body
```json
{
  "message": "How do I reset my password if I lost access to my email?",
  "session_id": "sess-9a8b7c",
  "workspace_id": 1
}
```

#### Response: Normal Grounded RAG (HTTP 200 OK)
```json
{
  "response": "To reset your password without email access: 1. Go to the login screen and click 'Forgot Password?'. 2. Verify using your backup phone number or security recovery key [doc-01]. If you do not have a recovery key, contact your organization administrator.",
  "citations": [
    {
      "doc_id": "doc-01",
      "title": "How to Reset Your CloudDesk / SmartDesk Password",
      "source_url": "/faq/auth/password-reset",
      "page": 1,
      "snippet": "To reset your password without email access: 1. Go to the login screen..."
    }
  ],
  "latency_ms": 922.74,
  "confidence": 0.92,
  "is_fallback": false,
  "fallback_reason": null,
  "escalation_recommended": false
}
```

#### Response: Fallback Mode (HTTP 200 OK - Circuit Breaker Tripped or Timeout)
```json
{
  "response": "We could not reach the real-time AI assistant. Based on our verified Knowledge Base, here is the relevant article: 'How to Reset Your CloudDesk / SmartDesk Password':\n\nTo reset your password: 1. Go to the login screen and click 'Forgot Password?'...",
  "citations": [
    {
      "doc_id": "doc-01",
      "title": "How to Reset Your CloudDesk / SmartDesk Password",
      "source_url": "/faq/auth/password-reset"
    }
  ],
  "latency_ms": 4012.30,
  "confidence": 0.55,
  "is_fallback": true,
  "fallback_reason": "FREE_TIER_RATE_LIMIT_COOLDOWN",
  "escalation_recommended": true
}
```

#### Error Response: Prompt Injection Detected (HTTP 400 Bad Request)
```json
{
  "detail": "Prompt rejected by security guardrail: Suspicious prompt token detected: 'ignore all previous instructions'",
  "error_code": "PROMPT_SECURITY_VIOLATION",
  "status_code": 400,
  "details": {}
}
```

---

## 2. Support Ticket Management

### `POST /api/v1/tickets`
Submit a new support inquiry or escalate from an unresolved chat session.

#### Request Body
```json
{
  "workspace_id": 1,
  "customer_name": "Nguyen Van A",
  "customer_email": "nguyenvana@example.com",
  "category": "Authentication",
  "priority": "Urgent",
  "subject": "Lost 2FA recovery token for corporate account",
  "description": "I changed my phone number and lost access to the authenticator app. Need urgent help resetting my corporate login."
}
```

#### Response (HTTP 201 Created)
```json
{
  "id": 1042,
  "workspace_id": 1,
  "ticket_code": "#TICK-1042",
  "customer_name": "Nguyen Van A",
  "customer_email": "nguyenvana@example.com",
  "category": "Authentication",
  "priority": "Urgent",
  "subject": "Lost 2FA recovery token for corporate account",
  "description": "I changed my phone number and lost access to the authenticator app. Need urgent help resetting my corporate login.",
  "status": "open",
  "ai_tags": [
    "Authentication",
    "Urgent",
    "2FA Recovery"
  ],
  "ai_draft_reply": "Dear Nguyen Van A,\n\nThank you for contacting SmartDesk AI Support...",
  "estimated_response_hours": 2,
  "created_at": "2026-09-13T15:30:00Z",
  "updated_at": "2026-09-13T15:30:00Z"
}
```

---

### `GET /api/v1/tickets`
Retrieve and filter tickets for the Support Agent Triage Dashboard.

#### Query Parameters
- `workspace_id`: Optional tenant filter (`1`, `2`, `3`, ...).
- `status`: Optional filter (`open`, `in_progress`, `resolved`, `closed`).
- `category`: Optional filter (`Authentication`, `Billing`, `Bug Report`, `Feature Request`, `General`; alias `Technical Bug` is also supported).
- `priority`: Optional filter (`Low`, `Medium`, `High`, `Urgent`).
- `search`: Optional query string matching subject, customer name, email, or `#TICK-XXXX`.
- `skip`: Pagination offset (default: 0).
- `limit`: Page size (default: 20, max: 100).

---

### `PATCH /api/v1/tickets/{ticket_id}`
Update ticket status or customize the pre-populated AI draft reply.

#### Request Body
```json
{
  "status": "in_progress",
  "ai_draft_reply": "Dear Nguyen Van A, I have manually verified your security profile and reset your MFA device. Please check your recovery phone."
}
```

---

## 3. Agent AI Copilot

### `POST /api/v1/agent/tickets/{ticket_id}/generate-draft`
Regenerate a tailored AI draft response for a ticket.

---

## 4. Knowledge Base & FAQ Retrieval

### `GET /api/v1/knowledge`
Retrieve verified FAQ knowledge articles supporting RAG grounding with optional category or keyword search.

#### Query Parameters
- `category`: Optional category filter (`Authentication`, `Billing`, `Bug Report`, `Feature Request`, `General`)
- `search`: Keyword search matching title or content

### `GET /api/v1/knowledge/{doc_id}`
Fetch a specific knowledge article by its document identifier (e.g. `doc-01`).

---

## 5. Health & Latency Benchmarks

### `GET /api/v1/health`
Operational readiness probe.

```json
{
  "status": "ok",
  "database": "connected",
  "version": "1.0.0"
}
```

### `GET /api/v1/health/smoke-test`
Executes an actual round-trip test against the active AI provider (`gemini-3.5-flash-lite` or `qwen2.5:3b`) and measures live latency.

---

## 6. Multi-Domain Workspaces API

### `GET /api/v1/workspaces`
Retrieve all registered business tenants / workspaces.

### `POST /api/v1/workspaces`
Register a new business domain workspace.

### `GET /api/v1/workspaces/{id}`
Fetch detailed workspace profile and rules by ID.

### `PUT /api/v1/workspaces/{id}`
Update persona attributes, tone of voice, or business rules.

---

## 7. Knowledge Ingestion & Active Verification Studio

### `POST /api/v1/workspaces/{workspace_id}/documents/upload`
Upload a `.pdf`, `.txt`, or `.md` file for text extraction, recursive chunking (600-800 chars, 100 overlap), and embedding.

### `GET /api/v1/documents/{document_id}/chunks`
Inspect extracted chunks and page locations of a document.

### `POST /api/v1/documents/{document_id}/verify`
Execute the 3-step Active Verification Engine: Synthetic QA Generation $\to$ Parallel RAG Self-Test $\to$ AI Judge Faithfulness Evaluation.

### `POST /api/v1/documents/{document_id}/publish`
Approve and publish a verified document into live production RAG.

### `DELETE /api/v1/documents/{document_id}`
Safely delete a document with cascade cleanup of all associated chunks, verification reports, and items.
