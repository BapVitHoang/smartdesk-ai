# SmartDesk AI — Frozen Architecture & Interface Contracts (`CONTRACTS.md`)

> **Status:** FROZEN  
> **Purpose:** Ensures zero merge conflicts across parallel multi-agent / multi-developer implementation of Phases B, C, and D.  
> **Module Ownership:**  
> - **Owner 1 (AI & Telemetry):** `llm_service.py`, `rag_service.py`, `ai_usage_logger.py`, `agent_tools.py`, `endpoints/ai_usage.py`, `endpoints/chat_stream.py`, `endpoints/chat_actions.py`  
> - **Owner 2 (Platform, Auth & Tickets):** `core/deps.py`, `models/user.py`, `models/ai_usage.py`, `endpoints/auth.py`, `db/seed/*`, `ticket_service.py`  
> - **Owner 3 (Frontend UX & DevOps):** `frontend/src/features/*`, `frontend/src/services/api/*`, `frontend/src/types/*`  
> - **Integration Owner:** `api/v1/api.py`, `core/config.py`, `db/session.py` (ALL changes must follow change-request process in `docs/requests/`)

---

## 1. Authentication & RBAC Dependencies (`backend/app/core/deps.py`)

```python
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_bearer)
) -> User:
    """
    Extracts Bearer JWT, validates HS256 signature, and resolves active User record.
    Fallback: returns default Admin User in development/testing mode when unauthenticated.
    """

def require_role(required_role: str) -> Callable:
    """
    FastAPI dependency factory enforcing role-based authorization.
    Returns 403 Forbidden if current_user.role != required_role (unless current_user.role == 'admin').
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
    status: str = "success",
    workspace_id: int = 1,
    session: Optional[AsyncSession] = None,
) -> None:
    """
    Persists AI telemetry records into `ai_usage_logs` table.
    Computes total_tokens = input_tokens + output_tokens.
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
    category: Literal["Authentication", "Billing", "Bug Report", "Technical Bug", "Feature Request", "General"]
    priority: Literal["Low", "Medium", "High", "Urgent"]
    ai_tags: List[str] = Field(min_length=1, max_length=5)
    sentiment: Literal["positive", "neutral", "frustrated", "urgent"] = "neutral"
    summary: str = Field(min_length=10, max_length=300)
    ai_draft_reply: str = Field(min_length=20)

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
    ) -> Tuple[str, float]: ...

    async def generate_structured_output(
        self,
        prompt: str,
        response_model: Type[Any],
        system_prompt: Optional[str] = None,
        temperature: float = 0.1,
    ) -> Tuple[Any, float]: ...

    async def generate_response_stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.2,
    ) -> AsyncGenerator[str, None]: ...
```

---

## 6. Pre-Registered API Routes (`backend/app/api/v1/api.py`)

| Prefix | Router Module | Owner | Purpose |
| :--- | :--- | :---: | :--- |
| `/chat` | `endpoints/chat.py` | Owner 1 | Core RAG answering & citations |
| `/chat` | `endpoints/chat_stream.py` | Owner 1 | SSE token-by-token streaming |
| `/chat` | `endpoints/chat_actions.py` | Owner 1 | Tool two-phase user confirmation |
| `/tickets` | `endpoints/tickets.py` | Owner 2 | Ticket CRUD, triage, filtering |
| `/agent` | `endpoints/agent.py` | Owner 2 | Copilot draft regeneration |
| `/agent/ai-usage` | `endpoints/ai_usage.py` | Owner 1 | AI usage & cost observability summary |
| `/knowledge` | `endpoints/knowledge.py` | Owner 1 | FAQ & Chunk detail lookup |
| `/health` | `endpoints/health.py` | Owner 2 | Healthchecks & smoke tests |
| `/workspaces` | `endpoints/workspaces.py` | Owner 2 | Multi-tenant workspace management |
| `""` | `endpoints/documents.py` | Owner 1 | Upload, verification, publishing |
| `/auth` | `endpoints/auth.py` | Owner 2 | OAuth2 login, JWT token, `/me` profile |
