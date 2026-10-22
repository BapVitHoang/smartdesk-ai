# SmartDesk AI - Formal API Specifications & Contract (v1)

> **Specification Version:** 1.2.0 (Frozen Integration Contract)  
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
  "type": "about:blank",
  "title": "Prompt Security Violation",
  "status": 400,
  "detail": "Yêu cầu bị từ chối do phát hiện dấu hiệu jailbreak hoặc prompt injection.",
  "code": "PROMPT_SECURITY_VIOLATION",
  "instance": "/api/v1/chat",
  "invalid_params": []
}
```
Canonical `code` values:
- `PROMPT_SECURITY_VIOLATION` (HTTP 400): Prompt injection or security guardrail triggered.
- `VALIDATION_ERROR` (HTTP 422 / 400): Request body or query parameter failed validation.
- `TICKET_NOT_FOUND` / `RESOURCE_NOT_FOUND` (HTTP 404): Requested entity does not exist.
- `UNAUTHORIZED` (HTTP 401): Missing or invalid Bearer JWT token.
- `FORBIDDEN` (HTTP 403): Insufficient role permissions (e.g. non-admin accessing admin route).
- `RATE_LIMITED` (HTTP 429): Rate limit exceeded or circuit breaker cooldown active.
- `INTERNAL_SERVER_ERROR` (HTTP 500): Unexpected server error (sanitized, never leaks stack traces).

---

## 1. Chat, RAG & Tool Calling Assistant

### `POST /api/v1/chat`
Ask questions to the customer support AI assistant with verified citation grounding, optional tool invocation, and automatic fallback.

#### Request Headers
- `Content-Type: application/json`

#### Request Body
```json
{
  "message": "Tạo giúp tôi ticket lỗi VNPAY mức Urgent",
  "session_id": "sess-9a8b7c",
  "workspace_id": 1
}
```

#### Response: Grounded RAG with Tool Execution Card (HTTP 200 OK)
```json
{
  "response": "Tôi đã chuẩn bị yêu cầu tạo ticket lỗi VNPAY mức độ Urgent cho bạn. Vui lòng xác nhận bên dưới.",
  "citations": [],
  "latency_ms": 842.15,
  "confidence": 0.95,
  "is_fallback": false,
  "fallback_reason": null,
  "escalation_recommended": false,
  "tools_called": ["create_escalation_ticket"],
  "pending_action": {
    "action_id": "act-9812",
    "action_type": "create_escalation_ticket",
    "summary": "Tạo ticket mới: Lỗi VNPAY (Urgent)",
    "parameters": {
      "subject": "Lỗi thanh toán cổng VNPAY",
      "priority": "Urgent",
      "category": "Billing"
    },
    "requires_confirmation": true,
    "expires_at": "2026-10-20T17:30:00Z"
  }
}
```

#### Response: Fallback Mode (HTTP 200 OK - Circuit Breaker Tripped or Timeout)
```json
{
  "response": "Hệ thống AI tạm thời đang ở chế độ dự phòng. Dựa trên dữ liệu đã xác minh: Để đặt lại mật khẩu: 1. Truy cập màn hình đăng nhập...",
  "citations": [
    {
      "doc_id": "doc-01",
      "title": "Hướng dẫn đặt lại mật khẩu SmartDesk",
      "source_url": "/faq/auth/password-reset"
    }
  ],
  "latency_ms": 4012.30,
  "confidence": 0.55,
  "is_fallback": true,
  "fallback_reason": "FREE_TIER_RATE_LIMIT_COOLDOWN",
  "escalation_recommended": true,
  "pending_action": null,
  "tools_called": []
}
```

---

### `POST /api/v1/chat/stream`
Token-by-token real-time streaming endpoint utilizing Server-Sent Events (SSE).

#### Request Headers
- `Accept: text/event-stream`
- `Content-Type: application/json`

#### Request Body
Same schema as `POST /api/v1/chat`.

#### SSE Stream Events:
```text
event: metadata
data: {"session_id":"sess-9a8b7c","model":"gemini-3.5-flash-lite","prompt_version":"v2.1"}

event: token
data: {"token":"Xin"}

event: token
data: {"token":" chào"}

event: token
data: {"token":" bạn!"}

event: done
data: {"response":"Xin chào bạn!","citations":[],"latency_ms":412.5,"confidence":0.98,"is_fallback":false,"fallback_reason":null,"escalation_recommended":false,"pending_action":null,"tools_called":[]}
```

---

### `POST /api/v1/chat/confirm-action`
Execute or cancel a pending mutating action generated by the agent.

#### Request Body
```json
{
  "action_id": "act-9812",
  "confirmed": true
}
```

#### Response (HTTP 200 OK)
```json
{
  "action_id": "act-9812",
  "status": "executed",
  "result_message": "Ticket #TICK-1043 đã được tạo thành công với mức ưu tiên Urgent.",
  "ticket_id": "#TICK-1043",
  "data": {
    "ticket_code": "#TICK-1043",
    "status": "open"
  }
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
  "customer_email": "an.nguyen@company.vn",
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
  "customer_email": "an.nguyen@company.vn",
  "category": "Authentication",
  "priority": "Urgent",
  "subject": "Lost 2FA recovery token for corporate account",
  "description": "I changed my phone number and lost access to the authenticator app. Need urgent help resetting my corporate login.",
  "status": "open",
  "ai_tags": ["Authentication", "Urgent", "2FA Recovery"],
  "ai_draft_reply": "Chào anh An, hệ thống SmartDesk đã tiếp nhận yêu cầu 2FA khẩn cấp của anh...",
  "estimated_response_hours": 2,
  "created_at": "2026-10-20T15:30:00Z",
  "updated_at": null
}
```

---

### `GET /api/v1/tickets`
Retrieve, filter, sort, and paginate tickets. Secured with JWT; user role sees only their own tickets, admin role sees all tickets.

#### Query Parameters
- `workspace_id`: Optional tenant filter (`1`, `2`, `3`, ...).
- `status`: Optional filter (`open`, `in_progress`, `resolved`).
- `category`: Optional filter (`Authentication`, `Billing`, `Bug Report`, `Feature Request`, `General`).
- `priority`: Optional filter (`Low`, `Medium`, `High`, `Urgent`).
- `sort_by`: `created_at` | `priority` | `status` | `sla_hours` (default: `created_at`).
- `sort_order`: `asc` | `desc` (default: `desc`).
- `page`: Page index $\ge 1$ (default: `1`).
- `page_size`: Page limit $\ge 1$ (default: `20`, max: `100`).

#### Response Headers
- `X-Total-Count: 42`

#### Response Body (HTTP 200 OK)
Array of `BackendTicketResponse` objects.

---

### `PATCH /api/v1/tickets/{ticket_id}`
Update ticket status or customize the pre-populated AI draft reply.

#### Request Body
```json
{
  "status": "in_progress",
  "ai_draft_reply": "Chào anh An, tôi đã kiểm tra hồ sơ và cấp lại mã khôi phục cho tài khoản của anh."
}
```

---

### `DELETE /api/v1/tickets/{ticket_id}`
Delete a ticket permanently (Admin only).
#### Response: `HTTP 204 No Content` (empty body).

---

## 3. Agent AI Copilot & Telemetry

### `POST /api/v1/agent/tickets/{ticket_id}/generate-draft`
Regenerate a tailored AI draft response for a ticket.

---

### `GET /api/v1/agent/ai-usage`
Retrieve aggregated token usage, cost tracking, latency metrics, and recent logs (Admin only).

#### Request Headers
- `Authorization: Bearer <admin-token>`

#### Response (HTTP 200 OK)
```json
{
  "total_requests": 142,
  "total_tokens": 128450,
  "total_cost_usd": 0.0428,
  "avg_latency_ms": 864.2,
  "fallback_count": 3,
  "refused_count": 2,
  "recent_logs": [
    {
      "id": 1,
      "trace_id": "tr-8921",
      "endpoint": "/api/v1/chat",
      "model_name": "gemini-3.5-flash-lite",
      "provider": "gemini",
      "prompt_tokens": 520,
      "completion_tokens": 110,
      "total_tokens": 630,
      "latency_ms": 812.4,
      "cost_usd": 0.00032,
      "status": "success",
      "created_at": "2026-10-20T17:15:00Z"
    }
  ]
}
```

---

### `POST /api/v1/agent/reset-cooldown`
1-click reset of the circuit breaker cooldown (Admin only).

#### Response (HTTP 200 OK)
```json
{
  "status": "success",
  "message": "Circuit breaker cooldown has been reset. Cloud Gemini calls re-enabled.",
  "cooldown_active": false
}
```

---

## 4. Knowledge Base & FAQ Retrieval

### `GET /api/v1/knowledge`
Retrieve verified FAQ knowledge articles supporting RAG grounding with optional category or keyword search.

### `GET /api/v1/knowledge/{doc_id}`
Fetch a specific knowledge article or chunk by its identifier (e.g. `doc-01` or `doc-1-chk-1`).

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

### `DELETE /api/v1/workspaces/{id}`
Delete a workspace (Admin only).
#### Response: `HTTP 204 No Content` (empty body).

---

## 7. Knowledge Ingestion & Active Verification Studio

### `POST /api/v1/workspaces/{workspace_id}/documents/upload`
Upload a `.pdf`, `.txt`, or `.md` file for text extraction, recursive chunking (600-800 chars, 100 overlap), and embedding.

### `GET /api/v1/documents/{document_id}/chunks`
Inspect extracted chunks and page locations of a document.

### `POST /api/v1/documents/{document_id}/verify`
Execute the 3-step Active Verification Engine: Synthetic QA Generation $\to$ Parallel RAG Self-Test $\to$ AI Judge Faithfulness Evaluation.

#### Response (HTTP 200 OK)
```json
{
  "id": 10,
  "document_id": 3,
  "workspace_id": 1,
  "faithfulness_score": 0.94,
  "status": "passed",
  "created_at": "2026-10-20T16:00:00Z",
  "items": [
    {
      "id": 1,
      "question": "Chính sách đổi trả trong vòng bao nhiêu ngày?",
      "ground_truth": "Trong vòng 30 ngày kể từ ngày mua hàng.",
      "rag_answer": "Sản phẩm được đổi trả trong 30 ngày.",
      "score": 1.0,
      "status": "passed",
      "reason": "Hoàn toàn khớp với nội dung tài liệu."
    }
  ],
  "agent_trace": [
    {
      "agent": "SyntheticQAExamAgent",
      "action": "generate_evaluation_questions",
      "input_summary": "Document chunks (700 chars)",
      "output_summary": "5 synthetic QA pairs generated",
      "latency_ms": 940.2,
      "status": "success",
      "timestamp": "2026-10-20T16:00:01Z"
    },
    {
      "agent": "SandboxRAGAgent",
      "action": "answer_synthetic_questions",
      "input_summary": "5 synthetic questions",
      "output_summary": "5 answers retrieved and generated",
      "latency_ms": 1120.5,
      "status": "success",
      "timestamp": "2026-10-20T16:00:03Z"
    },
    {
      "agent": "FaithfulnessJudgeAgent",
      "action": "evaluate_faithfulness",
      "input_summary": "5 RAG answers vs ground truth",
      "output_summary": "Faithfulness score: 0.94 (passed)",
      "latency_ms": 780.1,
      "status": "success",
      "timestamp": "2026-10-20T16:00:04Z"
    }
  ]
}
```

### `POST /api/v1/documents/{document_id}/publish`
Approve and publish a verified document into live production RAG.

### `DELETE /api/v1/documents/{document_id}`
Safely delete a document with cascade cleanup of all associated chunks, verification reports, and items.
#### Response: `HTTP 204 No Content` (empty body).

---

## 8. Authentication & RBAC (Hybrid OAuth2 & JWT)

### `POST /api/v1/auth/oauth2/login`
Authenticate via Google OAuth2 ID Token or 1-click Demo accounts (`admin@smartdesk.ai` or `an.nguyen@company.vn`).

#### Security & Verification Rules:
- **`provider: "google"`**: Requires valid Google ID token credential in `credential`. The backend cryptographically verifies token signature with Google public keys (`google-auth`), checks audience against `GOOGLE_OAUTH_CLIENT_ID`, checks issuer (`accounts.google.com`), checks expiry, and ensures `email_verified=true`. If `GOOGLE_OAUTH_CLIENT_ID` is not configured, returns `HTTP 501 Not Implemented`. Newly created Google users are assigned `role: "user"`; elevated to `"admin"` only if their email is listed in `ADMIN_EMAILS`.
- **`provider: "demo"`**: Available only when `DEMO_LOGIN_ENABLED=true` (default in dev, strictly false in shared/production deployments). Restricted to seeded accounts (`admin@smartdesk.ai`, `an.nguyen@company.vn`). Returns `HTTP 403 Forbidden` if demo login is disabled or if an unauthorized email is supplied. Never mints new accounts.

#### Request Body
```json
{
  "provider": "demo",
  "email": "admin@smartdesk.ai"
}
```
or with Google Credential:
```json
{
  "provider": "google",
  "credential": "<Google_ID_Token_JWT>"
}
```

#### Response (HTTP 200 OK)
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "role": "admin",
  "email": "admin@smartdesk.ai",
  "full_name": "Quản trị viên SmartDesk"
}
```

---

### `POST /api/v1/auth/token`
Standard OAuth2 password grant endpoint for automated API clients and customer credentials.

#### Security & Verification Rules:
- Verifies password against stored salted scrypt hash using constant-time comparison (`hmac.compare_digest`).
- Constant-time dummy verification runs even for unknown emails to eliminate user enumeration via timing attacks.
- Returns identical generic `HTTP 401 Unauthorized` (`"Tài khoản hoặc mật khẩu không chính xác."`) for wrong password, unknown user, or inactive account (`is_active=False`).
- Sliding-window in-memory throttle enforces rate limiting: returns `HTTP 429 Too Many Requests` after repeated failed attempts.

#### Request Body (`application/x-www-form-urlencoded` or JSON)
```json
{
  "username": "an.nguyen@company.vn",
  "password": "User@SmartDesk2026"
}
```

#### Response (HTTP 200 OK)
Same schema as `POST /api/v1/auth/oauth2/login`.

---

### `GET /api/v1/auth/me`
Retrieve currently authenticated user profile.

#### Request Headers
- `Authorization: Bearer <token>`

#### Response (HTTP 200 OK)
```json
{
  "id": 2,
  "email": "an.nguyen@company.vn",
  "full_name": "Nguyễn Văn An",
  "role": "user",
  "workspace_id": 1,
  "oauth_provider": "demo"
}
```
