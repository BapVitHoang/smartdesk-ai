# SmartDesk AI - API Specifications (v1)

This reference document defines the exact contract between the FastAPI backend and the Next.js frontend according to `DESIGN.md`.

---

## 1. Chat & RAG Endpoints

### `POST /api/v1/chat`
Ask a question to the customer support AI assistant with citation grounding and automatic fallback.

**Request Body:**
```json
{
  "message": "How do I reset my password if I lost access to my email?",
  "session_id": "sess-9a8b7c"
}
```

**Response (Normal RAG):**
```json
{
  "response": "To reset your password without email access: 1. Go to the login screen and click 'Need Help Signing In?'. 2. Verify using your backup phone number or security recovery key...",
  "citations": [
    {
      "doc_id": "doc-04",
      "title": "Account Recovery & 2FA Reset Guide",
      "source_url": "/docs/auth/account-recovery"
    }
  ],
  "latency_ms": 842.15,
  "confidence": 0.94,
  "is_fallback": false
}
```

**Response (Fallback Mode - Timeout or Outage):**
```json
{
  "response": "We could not reach the real-time AI assistant. Based on our verified Knowledge Base, here is the relevant article: 'How to Reset Your CloudDesk Password'...",
  "citations": [
    {
      "doc_id": "faq-01",
      "title": "Standard Password Reset",
      "source_url": "/faq/password-reset"
    }
  ],
  "latency_ms": 4012.30,
  "confidence": 0.40,
  "is_fallback": true,
  "escalation_recommended": true
}
```

---

## 2. Ticket Management Endpoints

### `POST /api/v1/tickets`
Create or escalate a customer support ticket.

**Request Body:**
```json
{
  "customer_name": "Nguyen Van A",
  "customer_email": "nguyenvana@example.com",
  "category": "Authentication",
  "priority": "Urgent",
  "subject": "Lost 2FA recovery token for corporate account",
  "description": "I changed my phone number and lost access to the authenticator app. Need help resetting."
}
```

**Response:**
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
  "ai_draft_reply": "Dear Nguyen Van A,\n\nWe understand that you have lost access to your 2FA authenticator...",
  "estimated_response_hours": 2,
  "created_at": "2026-09-13T15:30:00Z"
}
```

### `GET /api/v1/tickets`
List and filter tickets for the Support Agent Triage Dashboard.

**Query Parameters:**
- `status`: `open` | `in_progress` | `resolved`
- `category`: `Authentication` | `Billing` | `Technical Bug` | `Feature Request`
- `priority`: `Low` | `Medium` | `High` | `Urgent`
- `search`: String query matching subject or customer name.
- `skip`: Integer (default 0)
- `limit`: Integer (default 20)

### `PATCH /api/v1/tickets/{ticket_id}`
Update ticket status or customize the AI draft reply.

**Request Body:**
```json
{
  "status": "in_progress",
  "ai_draft_reply": "Customized reply written by the human support agent..."
}
```

---

## 3. Health & Latency Benchmarking

### `GET /api/v1/health`
Basic operational readiness.
```json
{
  "status": "ok",
  "database": "connected",
  "version": "1.0.0"
}
```

### `GET /api/v1/health/smoke-test`
Executes an actual round-trip test to the configured LLM and returns measured latency.
```json
{
  "model": "gemini-1.5-flash",
  "latency_ms": 852.53,
  "status": "PASS",
  "sample_prompt": "You are an AI Customer Support Assistant...",
  "sample_response": "Hello! If you cannot access your registered email..."
}
```
