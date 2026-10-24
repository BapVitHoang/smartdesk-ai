# SmartDesk AI — Frozen Architecture & Interface Contracts (`CONTRACTS.md`)

> **Status:** FROZEN INTEGRATION SPECIFICATION  
> **Purpose:** Ensures zero merge conflicts across parallel development of Phases B, C, and D.  
> **Team Structure (Exactly 3 Members):**
> - **Dev A (Owner 1):** AI Engine & Evaluation (`@TheOrijinnn`)  
> - **Dev B (Owner 2) & Integrator:** Platform, Data & Security + Integrator Hat (`@BapVitHoang`)  
> - **Dev C (Owner 3):** Frontend UX, QA & Capstone Documentation (`@TKhanh`)  
> *Note: Hoang is Dev B and simultaneously wears the Integrator hat. There is no separate fourth person.*

---

## 1. Authentication & RBAC Dependencies (`backend/app/core/deps.py`)

```python
async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Extracts Bearer JWT, validates HS256 signature, validates `exp` and `sub` claims,
    and resolves the active User entity from the database.
    
    STRICT SECURITY CONTRACT:
    - Returns HTTP 401 Unauthorized if no valid Bearer token is provided.
    - Rejects expired tokens, tokens with invalid signatures, and tokens with wrong algorithms.
    - Role is always queried from the persisted User record in the database, never trusted from JWT claims alone.
    - Inactive accounts (is_active=False) are rejected with HTTP 401.
    - Zero unauthenticated fallback: No DEV_AUTH_BYPASS or dummy admin returns exist in production code.
    - Tests use explicit dependency_overrides in conftest.py or real signed JWTs.
    """

def require_role(required_role: str) -> Callable:
    """
    FastAPI dependency factory enforcing role-based authorization.
    Returns HTTP 403 Forbidden if current_user.role != required_role (unless current_user.role == 'admin').
    """
```

---

## 2. AI Request Telemetry Logger (`backend/app/services/ai_usage_logger.py`)

```python
async def log_ai_call(
    endpoint: str,
    prompt_version: str,
    provider: str,
    model_name: str,
    tools_called: Optional[List[str]] = None,
    input_tokens: int = 0,
    output_tokens: int = 0,
    cost_usd: float = 0.0,
    latency_ms: float = 0.0,
    status: Literal["success", "fallback", "refused"] = "success",
    workspace_id: int = 1,
    session: Optional[AsyncSession] = None,
) -> None:
    """
    Persists AI telemetry records into `ai_usage_logs` table asynchronously.
    Computes total_tokens = input_tokens + output_tokens.
    Allowed status values:
      - 'success': Normal successful LLM call.
      - 'fallback': Circuit breaker tripped, timeout, or rate limit fallback.
      - 'refused': Guardrail triggered (prompt injection or out-of-scope query).
    """
```

---

## 3. Agent Tool Registry Interface (`backend/app/services/agent_tools.py`)

```python
ToolHandler = Callable[..., Awaitable[Dict[str, Any]]]

@dataclass
class ToolDefinition:
    name: str
    description: str
    parameters_schema: Dict[str, Any] = field(default_factory=dict)
    requires_confirmation: bool = False
    handler: Optional[ToolHandler] = None

class AgentToolRegistry:
    def register(self, tool: ToolDefinition) -> None: ...
    def get(self, name: str) -> Optional[ToolDefinition]: ...
    def list_tools(self) -> List[Dict[str, Any]]: ...

agent_tool_registry: AgentToolRegistry
```

---

## 4. Structured Output & Multi-Agent Tracing Schemas (`backend/app/schemas/ai_structured.py`)

```python
class TicketCopilotStructuredOutput(BaseModel):
    category: Literal["Authentication", "Billing", "Bug Report", "Feature Request", "General"]
    priority: Literal["Low", "Medium", "High", "Urgent"]
    ai_tags: List[str] = Field(min_length=1, max_length=5)
    sentiment: Literal["positive", "neutral", "frustrated", "urgent"] = "neutral"
    summary: str = Field(min_length=10, max_length=300)
    ai_draft_reply: str = Field(min_length=20)

    @field_validator("category", mode="before")
    @classmethod
    def normalize_category_alias(cls, v: str) -> str:
        """Normalizes legacy 'Technical Bug' alias to canonical 'Bug Report'."""
        if v == "Technical Bug":
            return "Bug Report"
        return v

class FaithfulnessJudgeStructuredOutput(BaseModel):
    score: float = Field(ge=0.0, le=1.0)
    status: Literal["passed", "warning", "failed"]
    reason: str
    missing_facts: List[str] = Field(default_factory=list)

class AgentHandOffStep(BaseModel):
    step_order: int
    from_agent: str
    to_agent: str
    action: str
    input_summary: str
    output_summary: str
    latency_ms: float
    status: Literal["success", "failed", "skipped"] = "success"
```

---

## 5. LLM Service Extensions (`backend/app/services/llm_service.py`)

```python
class LLMService:
    async def generate_response(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.2
    ) -> Tuple[str, float]:
        """
        Generates text completion.
        Returns: Tuple[response_text: str, latency_ms: float] where latency_ms is duration in milliseconds.
        """

    async def generate_structured_output(
        self,
        prompt: str,
        response_model: Type[Any],
        system_prompt: Optional[str] = None,
        temperature: float = 0.1,
    ) -> Tuple[Any, float]:
        """
        Generates validated Pydantic model output.
        Returns: Tuple[validated_instance: Any, latency_ms: float] where latency_ms is duration in milliseconds.
        """

    async def generate_response_stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.2,
    ) -> AsyncGenerator[str, None]:
        """
        Yields raw token strings as they arrive from the LLM stream.
        """
```

---

## 6. Pre-Registered API Routes (`backend/app/api/v1/api.py`)

| Prefix | Router Module | Owner | Purpose |
| :--- | :--- | :---: | :--- |
| `/chat` | `endpoints/chat.py` | Dev A | Core RAG answering & citations |
| `/chat` | `endpoints/chat_stream.py` | Dev A | SSE token-by-token streaming (`/chat/stream`) |
| `/chat` | `endpoints/chat_actions.py` | Dev A | Tool two-phase user confirmation (`/chat/confirm-action`) |
| `/agent/ai-usage` | `endpoints/ai_usage.py` | Dev A | AI usage & cost observability summary + reset-cooldown |
| `/knowledge` | `endpoints/knowledge.py` | Dev A | FAQ & Chunk detail lookup |
| `/tickets` | `endpoints/tickets.py` | Dev B | Ticket CRUD (POST requires Bearer auth), triage, server-side sorting, pagination, delete |
| `/agent` | `endpoints/agent.py` | Dev B | Copilot draft regeneration |
| `/workspaces` | `endpoints/workspaces.py` | Dev B | Workspace management & deletion |
| `/documents` | `endpoints/documents.py` | Dev B | Document upload, chunking & verification trigger |
| `/auth` | `endpoints/auth.py` | Dev B | OAuth2 login, JWT token, `/me` profile |
| `/health` | `endpoints/health.py` | Dev B | Healthchecks & smoke tests |

---

## 7. Ticket Copilot Service Contract (`backend/app/services/ticket_copilot_service.py`)

```python
async def generate_ticket_triage_and_draft(
    subject: str,
    description: str,
    workspace_id: int = 1,
    session: Optional[AsyncSession] = None,
) -> TicketCopilotStructuredOutput:
    """
    Invokes LLM single-call structured output to triage the ticket (category, priority, ai_tags, sentiment, summary)
    and produce a natural Vietnamese customer-facing draft reply.
    Falls back to deterministic rule-based output if LLM service is offline or in cooldown.
    """
```

---

## 8. HTTP and SSE Contracts

### 8.1 Standard RFC 7807 Error Response
Returned on all HTTP 4xx and 5xx errors:
```json
{
  "type": "about:blank",
  "title": "Prompt Security Violation",
  "status": 400,
  "detail": "Yêu cầu bị từ chối do phát hiện dấu hiệu jailbreak hoặc prompt injection.",
  "code": "PROMPT_SECURITY_VIOLATION",
  "instance": "/api/v1/chat"
}
```
**Canonical Error Codes:** `PROMPT_SECURITY_VIOLATION`, `UNAUTHORIZED`, `FORBIDDEN`, `TICKET_NOT_FOUND`, `RESOURCE_NOT_FOUND`, `VALIDATION_ERROR`, `RATE_LIMITED`, `INTERNAL_SERVER_ERROR`.

---

### 8.2 `POST /api/v1/chat` (With `pending_action` support)
**Request:**
```json
{
  "message": "Tạo giúp tôi ticket lỗi VNPAY mức Urgent",
  "session_id": "sess-12345",
  "workspace_id": 1
}
```
**Response (HTTP 200 OK):**
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

---

### 8.3 `POST /api/v1/chat/stream` (SSE Token-by-Token Streaming)
**Request Headers:** `Accept: text/event-stream`  
**Request Body:** Same as `/chat` (`message`, `session_id`, `workspace_id`)

**SSE Stream Output:**
```text
event: metadata
data: {"session_id":"sess-12345","model":"gemini-3.5-flash-lite","prompt_version":"v2.1"}

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

### 8.4 `POST /api/v1/chat/confirm-action`
**Request Body:**
```json
{
  "action_id": "act-9812",
  "confirmed": true
}
```
**Response (HTTP 200 OK):**
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

### 8.5 `POST /api/v1/auth/oauth2/login`
**Request Body:**
```json
{
  "provider": "demo",
  "email": "admin@smartdesk.ai"
}
```
**Response (HTTP 200 OK):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 86400,
  "user": {
    "id": 1,
    "email": "admin@smartdesk.ai",
    "full_name": "Quản trị viên SmartDesk",
    "role": "admin",
    "is_active": true
  }
}
```

---

### 8.6 `POST /api/v1/auth/token` (Standard OAuth2 Password Grant)
**Request Body (x-www-form-urlencoded or JSON):**
```json
{
  "username": "an.nguyen@company.vn",
  "password": "demopassword"
}
```
**Response (HTTP 200 OK):** Same schema as `AuthTokenResponse`.

---

### 8.7 `GET /api/v1/auth/me`
**Request Headers:** `Authorization: Bearer <token>`  
**Response (HTTP 200 OK):**
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

---

### 8.8 `GET /api/v1/agent/ai-usage`
**Request Headers:** `Authorization: Bearer <admin-token>`  
**Response (HTTP 200 OK):**
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

### 8.9 `POST /api/v1/agent/reset-cooldown`
**Request Headers:** `Authorization: Bearer <admin-token>`  
**Response (HTTP 200 OK):**
```json
{
  "status": "success",
  "message": "Circuit breaker cooldown has been reset. Cloud Gemini calls re-enabled.",
  "cooldown_active": false
}
```

---

### 8.9a `POST /api/v1/tickets` (Authenticated Creation & Tenant Binding)
**Request Headers:** `Authorization: Bearer <token>`, `Content-Type: application/json`  
**Description:** Requires authenticated session (`get_current_user`). For standard customers (`role == "user"`), ticket `customer_email` and `customer_name` are strictly locked to the token owner, preventing customer spoofing. Support staff (`admin`) can submit on behalf of customers.  
**Response (HTTP 201 Created):** `TicketResponse` object.  
**Errors:** `401 Unauthorized` if unauthenticated.

---

### 8.10 `GET /api/v1/tickets` (With Server Sort, Pagination & `X-Total-Count`)
**Query Parameters:**
- `status`: Optional filter (`open`, `in_progress`, `resolved`).
- `category`: Optional filter (`Authentication`, `Billing`, `Bug Report`, etc.).
- `priority`: Optional filter (`Low`, `Medium`, `High`, `Urgent`).
- `sort_by`: `created_at` | `priority` | `status` | `sla_hours` (default `created_at`).
- `sort_order`: `asc` | `desc` (default `desc`).
- `page`: int $\ge 1$ (default `1`).
- `page_size`: int $\ge 1$ (default `20`).

**Response Headers:**
- `X-Total-Count: 42`

**Response Body (HTTP 200 OK):**
```json
[
  {
    "id": 1,
    "workspace_id": 1,
    "ticket_code": "#TICK-1042",
    "customer_name": "Nguyễn Văn An",
    "customer_email": "an.nguyen@company.vn",
    "category": "Bug Report",
    "priority": "High",
    "subject": "Không đăng nhập được qua SSO",
    "description": "Tôi thử đăng nhập bằng Google SSO nhưng nhận lỗi 403 Forbidden.",
    "status": "open",
    "ai_tags": ["SSO", "Auth", "Google"],
    "ai_draft_reply": "Chào anh An, hệ thống đã ghi nhận lỗi SSO của anh...",
    "estimated_response_hours": 4,
    "created_at": "2026-10-20T14:30:00Z",
    "updated_at": null
  }
]
```

---

### 8.11 `DELETE /api/v1/tickets/{ticket_id}` & `DELETE /api/v1/workspaces/{workspace_id}`
**Response:** `HTTP 204 No Content` (empty body).

---

### 8.12 Document Verification Report with Multi-Agent Trace
`GET /api/v1/documents/{document_id}/verify` or `POST /api/v1/documents/{document_id}/verify`
**Response (HTTP 200 OK):**
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
