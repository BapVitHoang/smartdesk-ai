# SmartDesk AI - Formal API Specifications & Contract (v1)

> **Specification Version:** 1.0.0  
> **Base URL:** `http://localhost:8000/api/v1`  
> **Architecture Status:** Full Enterprise System Integration (Frontend & Backend)

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
  "session_id": "sess-9a8b7c"
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
      "source_url": "/faq/auth/password-reset"
    }
  ],
  "latency_ms": 782.45,
  "confidence": 0.92,
  "is_fallback": false,
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
  "ai_draft_reply": "Dear Nguyen Van A,\n\nThank you for contacting SmartDesk AI Support. We have received your inquiry regarding \"Lost 2FA recovery token for corporate account\" and our support team has categorized it as [Authentication] with [Urgent] priority.\n\nBased on our support policies for Authentication:\n1. Our engineering team is currently verifying the status of your account and system logs.\n2. In the meantime, if you have any additional error codes, screenshots, or logs, please reply directly to this thread.\n3. You will receive an update from a dedicated specialist within our 2-hour SLA window.\n\nWe appreciate your patience while we investigate this matter for you.\n\nWarm regards,\nSmartDesk Support Team",
  "estimated_response_hours": 2,
  "created_at": "2026-09-13T15:30:00Z",
  "updated_at": "2026-09-13T15:30:00Z"
}
```

---

### `GET /api/v1/tickets`
Retrieve and filter tickets for the Support Agent Triage Dashboard.

#### Query Parameters
- `status`: Optional filter (`open`, `in_progress`, `resolved`, `closed`).
- `category`: Optional filter (`Authentication`, `Billing`, `Technical Bug`, `Feature Request`).
- `priority`: Optional filter (`Low`, `Medium`, `High`, `Urgent`).
- `search`: Optional query string matching subject, customer name, email, or `#TICK-XXXX`.
- `skip`: Pagination offset (default: 0).
- `limit`: Page size (default: 20, max: 100).

#### Response (HTTP 200 OK)
```json
[
  {
    "id": 1042,
    "ticket_code": "#TICK-1042",
    "customer_name": "Nguyen Van A",
    "customer_email": "nguyenvana@example.com",
    "category": "Authentication",
    "priority": "Urgent",
    "subject": "Lost 2FA recovery token for corporate account",
    "description": "I changed my phone number...",
    "status": "open",
    "ai_tags": ["Authentication", "Urgent", "2FA Recovery"],
    "ai_draft_reply": "Dear Nguyen Van A...",
    "estimated_response_hours": 2,
    "created_at": "2026-09-13T15:30:00Z",
    "updated_at": "2026-09-13T15:30:00Z"
  }
]
```

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

#### Response (HTTP 200 OK)
```json
{
  "id": 1042,
  "ticket_code": "#TICK-1042",
  "customer_name": "Nguyen Van A",
  "customer_email": "nguyenvana@example.com",
  "category": "Authentication",
  "priority": "Urgent",
  "subject": "Lost 2FA recovery token for corporate account",
  "description": "I changed my phone number...",
  "status": "in_progress",
  "ai_tags": ["Authentication", "Urgent", "2FA Recovery"],
  "ai_draft_reply": "Dear Nguyen Van A, I have manually verified your security profile and reset your MFA device. Please check your recovery phone.",
  "estimated_response_hours": 2,
  "created_at": "2026-09-13T15:30:00Z",
  "updated_at": "2026-09-13T15:35:10Z"
}
```

---

## 3. Agent AI Copilot

### `POST /api/v1/agent/tickets/{ticket_id}/generate-draft`
Regenerate a tailored AI draft response for a ticket.

#### Response (HTTP 200 OK)
```json
{
  "id": 1042,
  "ticket_code": "#TICK-1042",
  "customer_name": "Nguyen Van A",
  "customer_email": "nguyenvana@example.com",
  "category": "Authentication",
  "priority": "Urgent",
  "subject": "Lost 2FA recovery token for corporate account",
  "description": "I changed my phone number...",
  "status": "open",
  "ai_tags": ["Authentication", "Urgent", "2FA Recovery"],
  "ai_draft_reply": "Dear Nguyen Van A,\n\nWe understand that you are locked out due to an authenticator change. As an urgent priority ticket, our Tier 2 security team has initiated an identity verification protocol...",
  "estimated_response_hours": 2,
  "created_at": "2026-09-13T15:30:00Z",
  "updated_at": "2026-09-13T15:36:00Z"
}
```

---

## 4. Knowledge Base & FAQ Retrieval

### `GET /api/v1/knowledge`
Retrieve verified FAQ knowledge articles supporting RAG grounding with optional category or keyword search.

#### Query Parameters
- `category`: Optional category filter (`Authentication`, `Billing`, `Technical Bug`, etc.)
- `search`: Keyword search matching title or content

#### Response (HTTP 200 OK)
```json
[
  {
    "doc_id": "doc-01",
    "category": "Authentication",
    "title": "How to Reset Your CloudDesk / SmartDesk Password",
    "content": "To reset your password without email access: 1. Go to the login screen...",
    "source_url": "/faq/auth/password-reset"
  }
]
```

---

### `GET /api/v1/knowledge/{doc_id}`
Fetch a specific knowledge article by its document identifier (e.g. `doc-01`).

#### Response (HTTP 200 OK)
```json
{
  "doc_id": "doc-01",
  "category": "Authentication",
  "title": "How to Reset Your CloudDesk / SmartDesk Password",
  "content": "To reset your password without email access: 1. Go to the login screen...",
  "source_url": "/faq/auth/password-reset"
}
```

---

## 5. Health & Latency Benchmarks

### `GET /api/v1/health`
Operational readiness probe.

#### Response (HTTP 200 OK)
```json
{
  "status": "ok",
  "database": "connected",
  "version": "1.0.0"
}
```

---

### `GET /api/v1/health/smoke-test`
Executes an actual round-trip test against Google Gemini 1.5 Flash and measures latency.

#### Response (HTTP 200 OK)
```json
{
  "model": "gemini-1.5-flash",
  "latency_ms": 852.53,
  "status": "PASS",
  "sample_prompt": "You are an AI Customer Support Assistant. Briefly greet the user in one sentence and explain how to reset a password.",
  "sample_response": "Hello! To reset your password, visit the login page, click 'Forgot Password?', and enter your email address to receive a secure reset link."
}
```
