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
Executes an actual round-trip test against Google Gemini 3.5 Flash Lite and measures live latency.

#### Response (HTTP 200 OK)
```json
{
  "model": "gemini-3.5-flash-lite",
  "latency_ms": 922.74,
  "status": "PASS",
  "sample_prompt": "You are an AI Customer Support Assistant. Briefly greet the user in one sentence and explain how to reset a password.",
  "sample_response": "Hello! To reset your password, visit the login page, click 'Forgot Password?', and enter your email address to receive a secure reset link."
}
```

---

## 6. Multi-Domain Workspaces API

### `GET /api/v1/workspaces`
Retrieve all registered business tenants / workspaces.

#### Response (HTTP 200 OK)
```json
[
  {
    "id": 1,
    "slug": "default",
    "name": "SmartDesk Cloud Support",
    "industry": "IT & SaaS",
    "persona_name": "SmartDesk Assistant",
    "tone_of_voice": "Chuyên nghiệp, ngắn gọn, thân thiện và chính xác về mặt kỹ thuật.",
    "business_rules": "Hỗ trợ xử lý sự cố tài khoản, phân quyền, tích hợp API, thanh toán định kỳ. Luôn bảo vệ an toàn thông tin khách hàng.",
    "created_at": "2026-09-27T08:00:00Z"
  }
]
```

---

### `POST /api/v1/workspaces`
Register a new business domain workspace.

#### Request Body
```json
{
  "slug": "smilecare",
  "name": "Nha Khoa Thẩm Mỹ SmileCare",
  "industry": "Y tế & Nha khoa",
  "persona_name": "Bác sĩ SmileCare Bot",
  "tone_of_voice": "Ân cần, chu đáo, đồng cảm, chuyên môn y khoa cao nhưng dễ hiểu.",
  "business_rules": "Tư vấn niềng răng, bọc sứ, tẩy trắng, cấy ghép Implant. Báo giá minh bạch."
}
```

#### Response (HTTP 201 Created)
```json
{
  "id": 2,
  "slug": "smilecare",
  "name": "Nha Khoa Thẩm Mỹ SmileCare",
  "industry": "Y tế & Nha khoa",
  "persona_name": "Bác sĩ SmileCare Bot",
  "tone_of_voice": "Ân cần, chu đáo, đồng cảm, chuyên môn y khoa cao nhưng dễ hiểu.",
  "business_rules": "Tư vấn niềng răng, bọc sứ, tẩy trắng, cấy ghép Implant. Báo giá minh bạch.",
  "created_at": "2026-09-27T08:30:00Z"
}
```

---

### `GET /api/v1/workspaces/{id}`
Fetch detailed workspace profile and rules by ID.

---

### `PUT /api/v1/workspaces/{id}`
Update persona attributes, tone of voice, or business rules.

---

## 7. Knowledge Ingestion & Active Verification Studio

### `POST /api/v1/workspaces/{workspace_id}/documents/upload`
Upload a `.pdf`, `.txt`, or `.md` file for text extraction, recursive chunking (600-800 chars, 100 overlap), and embedding.

#### Request Form Data
- `file`: Binary file upload (`multipart/form-data`)

#### Response (HTTP 201 Created)
```json
{
  "id": 10,
  "workspace_id": 2,
  "filename": "bang_gia_dich_vu_smilecare.txt",
  "file_type": "txt",
  "file_size": 2048,
  "status": "pending",
  "chunk_count": 3,
  "created_at": "2026-09-27T09:00:00Z"
}
```

---

### `GET /api/v1/documents/{document_id}/chunks`
Inspect extracted chunks and page locations of a document.

#### Response (HTTP 200 OK)
```json
[
  {
    "id": 45,
    "chunk_id": "doc-10-chk-1",
    "chunk_index": 0,
    "page_number": 1,
    "title": "bang_gia_dich_vu_smilecare.txt - Trang 1 (Mục 1)",
    "content": "BẢNG GIÁ DỊCH VỤ NHA KHOA SMILECARE...",
    "source_url": "/documents/10/page/1"
  }
]
```

---

### `POST /api/v1/documents/{document_id}/verify`
Execute the 3-step Active Verification Engine: Synthetic QA Generation $\to$ Parallel RAG Self-Test $\to$ AI Judge Faithfulness Evaluation.

#### Response (HTTP 200 OK)
```json
{
  "id": 4,
  "document_id": 10,
  "workspace_id": 2,
  "faithfulness_score": 0.95,
  "status": "passed",
  "created_at": "2026-09-27T09:05:00Z",
  "items": [
    {
      "id": 12,
      "question": "Chi phí tẩy trắng răng tại SmileCare là bao nhiêu?",
      "ground_truth": "Tẩy trắng răng bằng công nghệ Laser White có giá 2.500.000 VNĐ một liệu trình 60 phút.",
      "rag_answer": "Dịch vụ tẩy trắng răng Laser White tại SmileCare có giá 2.500.000 VNĐ cho liệu trình 60 phút.",
      "score": 0.98,
      "status": "passed",
      "reason": "Câu trả lời bám sát và chính xác tuyệt đối với tài liệu gốc."
    }
  ]
}
```

---

### `POST /api/v1/documents/{document_id}/publish`
Approve and publish a verified document into live production RAG.

#### Response (HTTP 200 OK)
```json
{
  "id": 10,
  "status": "published",
  "message": "Đã xuất bản tài liệu thành công ra Chatbot."
}
```

---

### `DELETE /api/v1/documents/{document_id}`
Safely delete a document with cascade cleanup of all associated chunks, verification reports, and items.
```json
{
  "ok": true,
  "message": "Đã xóa thành công tài liệu ID 10."
}
```
