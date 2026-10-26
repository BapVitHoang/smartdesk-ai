"""Agent Tool Registry, 4 DB-Backed Support Tools, Single-Pass Tool Router, and Two-Phase User Confirmation Store (Capability B - REQ-14)."""

from dataclasses import dataclass, field
import datetime
import logging
import re
import uuid
from typing import Any, Awaitable, Callable, Dict, List, Optional
from sqlalchemy import desc, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.knowledge import FAQItem, KnowledgeChunk
from app.models.ticket import Ticket
from app.schemas.chat import PendingActionSchema
from app.schemas.ticket import TicketCreate
from app.services.fallback_service import fallback_service
from app.services.ticket_copilot_service import ticket_copilot_service
from app.services.ticket_service import ticket_service

logger = logging.getLogger("smartdesk.agent_tools")

ToolHandler = Callable[..., Awaitable[Dict[str, Any]]]


def _get_user_attr(user: Any, attr: str, default: Any = None) -> Any:
    """Safely extracts an attribute whether user is an ORM model, dict, or None."""
    if user is None:
        return default
    if isinstance(user, dict):
        return user.get(attr, default)
    return getattr(user, attr, default)


@dataclass
class ToolDefinition:
    """Metadata and async handler for a callable support agent tool."""

    name: str
    description: str
    parameters_schema: Dict[str, Any] = field(default_factory=dict)
    requires_confirmation: bool = False
    handler: Optional[ToolHandler] = None


class AgentToolRegistry:
    """Central registry for support agent tools and server-side pending confirmation actions."""

    def __init__(self) -> None:
        self._tools: Dict[str, ToolDefinition] = {}
        self._pending_actions: Dict[str, Dict[str, Any]] = {}

    def register(self, tool: ToolDefinition) -> None:
        """Register a tool definition by name."""
        self._tools[tool.name] = tool

    def get(self, name: str) -> Optional[ToolDefinition]:
        """Retrieve a registered tool definition."""
        return self._tools.get(name)

    def list_tools(self) -> List[Dict[str, Any]]:
        """Return serializable tool specifications for LLM tool-calling."""
        return [
            {
                "name": t.name,
                "description": t.description,
                "parameters": t.parameters_schema,
                "requires_confirmation": t.requires_confirmation,
            }
            for t in self._tools.values()
        ]

    def create_pending_action(
        self,
        action_type: str,
        summary: str,
        parameters: Dict[str, Any],
        creator_id: Optional[int] = None,
        creator_email: Optional[str] = None,
    ) -> PendingActionSchema:
        """Stores a mutating tool action awaiting explicit user confirmation."""
        action_id = f"act-{uuid.uuid4().hex[:6]}"
        expires_dt = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=30)
        expires_iso = expires_dt.strftime("%Y-%m-%dT%H:%M:%SZ")

        record = {
            "action_id": action_id,
            "action_type": action_type,
            "summary": summary,
            "parameters": parameters,
            "requires_confirmation": True,
            "expires_at": expires_iso,
            "status": "pending",
            "creator_id": creator_id,
            "creator_email": creator_email,
        }
        self._pending_actions[action_id] = record
        return PendingActionSchema(
            action_id=action_id,
            action_type=action_type,
            summary=summary,
            parameters=parameters,
            requires_confirmation=True,
            expires_at=expires_iso,
        )

    def get_pending_action(self, action_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves a pending action by ID."""
        return self._pending_actions.get(action_id)

    async def execute_pending_action(
        self,
        action_id: str,
        confirmed: bool,
        db: Optional[AsyncSession] = None,
        current_user: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Executes or cancels a stored pending action upon user confirmation."""
        pending = self._pending_actions.get(action_id)

        # 1. Unknown action ID
        if not pending:
            return {
                "action_id": action_id,
                "status": "not_found",
                "error_code": "ACTION_NOT_FOUND",
                "executed": False,
                "result_message": "Không tìm thấy yêu cầu xác thực hoặc mã hành động không hợp lệ.",
                "message": "Không tìm thấy yêu cầu xác thực hoặc mã hành động không hợp lệ.",
                "ticket_id": None,
                "data": {"status": "not_found"},
            }

        # 2. Already executed or cancelled
        if pending.get("status") in ("executed", "cancelled", "already_executed"):
            return {
                "action_id": action_id,
                "status": "already_executed",
                "error_code": "ALREADY_EXECUTED",
                "executed": False,
                "result_message": "Hành động này đã được xử lý trước đó và không thể thực thi lại.",
                "message": "Hành động này đã được xử lý trước đó và không thể thực thi lại.",
                "ticket_id": pending.get("ticket_code"),
                "data": {"status": pending.get("status")},
            }

        # 3. Check expiration
        expires_at_str = pending.get("expires_at")
        if expires_at_str:
            try:
                clean_exp = expires_at_str.replace("Z", "+00:00")
                exp_dt = datetime.datetime.fromisoformat(clean_exp)
                if datetime.datetime.now(datetime.timezone.utc) > exp_dt:
                    pending["status"] = "expired"
                    return {
                        "action_id": action_id,
                        "status": "expired",
                        "error_code": "ACTION_EXPIRED",
                        "executed": False,
                        "result_message": "Yêu cầu xác nhận đã hết hạn hiệu lực (30 phút).",
                        "message": "Yêu cầu xác nhận đã hết hạn hiệu lực (30 phút).",
                        "ticket_id": None,
                        "data": {"status": "expired"},
                    }
            except Exception as e:
                logger.warning(f"Error parsing expires_at: {e}")

        # 4. Cancellation path (clean abort without mutating state)
        if not confirmed:
            pending["status"] = "cancelled"
            return {
                "action_id": action_id,
                "status": "cancelled",
                "executed": False,
                "result_message": "Thao tác đã bị người dùng hủy bỏ.",
                "message": "Thao tác đã bị người dùng hủy bỏ.",
                "ticket_id": None,
                "data": {"status": "cancelled"},
            }

        # 5. User scoping & RBAC isolation for action confirmation
        user_role = _get_user_attr(current_user, "role", None)
        user_id = _get_user_attr(current_user, "id", None)
        user_email = str(_get_user_attr(current_user, "email", "") or "").lower()
        c_id = pending.get("creator_id")
        c_email = str(pending.get("creator_email", "") or "").lower()

        # Decision Option A: Mutating ticket status or priority is strictly restricted to Admins
        if pending.get("action_type") == "update_ticket_priority_or_status" and user_role != "admin":
            return {
                "action_id": action_id,
                "status": "forbidden",
                "error_code": "ACTION_FORBIDDEN",
                "executed": False,
                "result_message": "Quyền truy cập bị từ chối: Thao tác cập nhật trạng thái/độ ưu tiên ticket chỉ dành cho Quản trị viên (Admin).",
                "message": "Quyền truy cập bị từ chối: Thao tác cập nhật trạng thái/độ ưu tiên ticket chỉ dành cho Quản trị viên (Admin).",
                "ticket_id": None,
                "data": {"status": "forbidden"},
            }

        # General creator isolation: Non-admin users cannot confirm actions created by another authenticated user
        if user_role != "admin":
            has_mismatch = False
            if c_id is not None:
                if current_user is None or user_id != c_id:
                    has_mismatch = True
            elif c_email and current_user is not None and user_email and c_email != user_email:
                has_mismatch = True

            if has_mismatch:
                return {
                    "action_id": action_id,
                    "status": "forbidden",
                    "error_code": "ACTION_FORBIDDEN",
                    "executed": False,
                    "result_message": "Quyền truy cập bị từ chối: Bạn không có quyền xác nhận hành động của người dùng khác.",
                    "message": "Quyền truy cập bị từ chối: Bạn không có quyền xác nhận hành động của người dùng khác.",
                    "ticket_id": None,
                    "data": {"status": "forbidden"},
                }

        action_type = pending["action_type"]
        params = pending.get("parameters", {})

        if action_type == "create_escalation_ticket" and db is not None:
            ticket_in = TicketCreate(
                workspace_id=int(params.get("workspace_id", 1)),
                customer_name=str(params.get("customer_name", "Khách hàng Chat")),
                customer_email=str(params.get("customer_email", "an.nguyen@company.vn")),
                subject=str(params.get("subject", "Yêu cầu hỗ trợ từ AI Chat")),
                description=str(params.get("description", params.get("subject", "Yêu cầu hỗ trợ kỹ thuật cần xử lý.")))
                if len(str(params.get("description", ""))) >= 10
                else f"Yêu cầu hỗ trợ từ AI Chat: {params.get('subject', 'Cần chuyên viên kiểm tra')}",
                category=str(params.get("category", "General")),
                priority=str(params.get("priority", "High")),
            )
            created = await ticket_service.create_ticket(db, ticket_in)
            pending["status"] = "executed"
            pending["ticket_code"] = created.ticket_code
            sla_h = getattr(created, "estimated_response_hours", getattr(created, "sla_hours", 8))
            msg = f"Ticket {created.ticket_code} đã được tạo thành công với mức ưu tiên {created.priority} (SLA: {sla_h}h)."
            return {
                "action_id": action_id,
                "status": "executed",
                "executed": True,
                "result_message": msg,
                "message": msg,
                "ticket_id": created.ticket_code,
                "data": {
                    "ticket_code": created.ticket_code,
                    "status": created.status,
                    "priority": created.priority,
                    "category": created.category,
                    "sla_hours": sla_h,
                },
            }

        if action_type == "update_ticket_priority_or_status" and db is not None:
            ticket_code = str(params.get("ticket_code", "#TICK-1042"))
            formatted_code = ticket_code if ticket_code.startswith("#") else f"#{ticket_code}"
            new_priority = params.get("priority")
            new_status = params.get("status")

            res = await db.execute(
                select(Ticket).where(
                    or_(Ticket.ticket_code == ticket_code, Ticket.ticket_code == formatted_code)
                )
            )
            ticket_obj = res.scalars().first()
            if ticket_obj:
                if new_priority:
                    ticket_obj.priority = str(new_priority)
                    ticket_obj.estimated_response_hours = ticket_service.calculate_sla_hours(str(new_priority))
                if new_status:
                    ticket_obj.status = str(new_status)
                await db.commit()
                await db.refresh(ticket_obj)
                pending["status"] = "executed"
                pending["ticket_code"] = ticket_obj.ticket_code
                sla_h = getattr(ticket_obj, "estimated_response_hours", 8)
                msg = (
                    f"Đã cập nhật thành công ticket {ticket_obj.ticket_code}: "
                    f"Trạng thái = {ticket_obj.status}, Mức ưu tiên = {ticket_obj.priority} (SLA {sla_h}h)."
                )
                return {
                    "action_id": action_id,
                    "status": "executed",
                    "executed": True,
                    "result_message": msg,
                    "message": msg,
                    "ticket_id": ticket_obj.ticket_code,
                    "data": {
                        "ticket_code": ticket_obj.ticket_code,
                        "status": ticket_obj.status,
                        "priority": ticket_obj.priority,
                        "sla_hours": sla_h,
                    },
                }

        pending["status"] = "executed"
        msg = f"Đã xác nhận và thực thi thao tác '{action_type}' thành công."
        return {
            "action_id": action_id,
            "status": "executed",
            "executed": True,
            "result_message": msg,
            "message": msg,
            "ticket_id": params.get("ticket_code"),
            "data": {"status": "executed", **params},
        }


# --- Tool Handlers ---

async def handle_lookup_customer_tickets(
    session: Optional[AsyncSession] = None,
    customer_email: Optional[str] = None,
    ticket_code: Optional[str] = None,
    workspace_id: int = 1,
    current_user: Optional[Any] = None,
) -> Dict[str, Any]:
    """Tool 1: Read-only lookup of customer support tickets by email or #TICK-XXXX code."""
    if session is None:
        return {
            "found": False,
            "tickets": [],
            "message": "Không thể kết nối cơ sở dữ liệu để tra cứu ticket.",
        }

    query = select(Ticket)

    # Scoping rule: Non-admin users are strictly constrained to their own tickets
    if current_user and getattr(current_user, "role", "user") != "admin":
        user_email = getattr(current_user, "email", "")
        query = query.where(Ticket.customer_email.ilike(user_email))

    if ticket_code:
        formatted = ticket_code.upper() if ticket_code.startswith("#") else f"#{ticket_code.upper()}"
        query = query.where(or_(Ticket.ticket_code.ilike(ticket_code), Ticket.ticket_code.ilike(formatted)))
    elif customer_email:
        query = query.where(Ticket.customer_email.ilike(customer_email))
    else:
        query = query.where(Ticket.workspace_id == workspace_id)

    query = query.order_by(desc(Ticket.created_at)).limit(5)
    res = await session.execute(query)
    tickets = res.scalars().all()

    if not tickets:
        target_label = ticket_code or customer_email or f"Workspace #{workspace_id}"
        return {
            "found": False,
            "tickets": [],
            "message": f"Không tìm thấy phiếu hỗ trợ (ticket) nào khớp với thông tin '{target_label}'.",
        }

    items = []
    lines = ["Kết quả tra cứu phiếu hỗ trợ trực tiếp từ hệ thống:"]
    for t in tickets:
        sla_h = getattr(t, "estimated_response_hours", getattr(t, "sla_hours", 8))
        status_vi = {
            "open": "Đang mở (Open)",
            "in_progress": "Đang xử lý (Pending)",
            "resolved": "Đã giải quyết (Resolved)",
        }.get(t.status, t.status)
        lines.append(
            f"- **{t.ticket_code}**: \"{t.subject}\" | Danh mục: `{t.category}` | "
            f"Ưu tiên: `{t.priority}` (SLA: {sla_h}h) | Trạng thái: **{status_vi}** | Khách hàng: `{t.customer_email}`"
        )
        items.append({
            "ticket_code": t.ticket_code,
            "subject": t.subject,
            "category": t.category,
            "priority": t.priority,
            "status": t.status,
            "sla_hours": sla_h,
            "customer_email": t.customer_email,
        })

    return {
        "found": True,
        "tickets": items,
        "message": "\n".join(lines),
    }


async def handle_search_workspace_knowledge(
    query: str,
    workspace_id: int = 1,
    session: Optional[AsyncSession] = None,
) -> Dict[str, Any]:
    """Tool 2: Read-only search over published workspace knowledge chunks and curated FAQs."""
    matches: List[Dict[str, Any]] = []
    if session is not None:
        chunk_res = await session.execute(
            select(KnowledgeChunk)
            .where(KnowledgeChunk.workspace_id == workspace_id)
            .limit(10)
        )
        for chk in chunk_res.scalars().all():
            if any(tok in chk.content.lower() for tok in query.lower().split() if len(tok) > 2):
                matches.append({
                    "doc_id": chk.chunk_id,
                    "title": chk.title,
                    "snippet": chk.content[:180],
                })

    if not matches and workspace_id == 1:
        fb = fallback_service.match_faq(query, workspace_id=1)
        return {
            "found": len(fb.get("citations", [])) > 0,
            "results": fb.get("citations", []),
            "message": fb.get("response", ""),
        }

    return {
        "found": len(matches) > 0,
        "results": matches[:3],
        "message": f"Tìm thấy {len(matches[:3])} đoạn tài liệu liên quan trong Workspace #{workspace_id}.",
    }


async def handle_prepare_escalation_ticket(
    registry: AgentToolRegistry,
    subject: str,
    description: str,
    priority: str = "High",
    category: str = "General",
    customer_email: str = "an.nguyen@company.vn",
    customer_name: str = "Nguyễn Văn An",
    workspace_id: int = 1,
    creator_id: Optional[int] = None,
    creator_email: Optional[str] = None,
) -> Dict[str, Any]:
    """Tool 3: Mutating tool that prepares a PendingAction to create an escalation support ticket (requires user confirmation)."""
    norm_category = ticket_copilot_service.infer_category(f"{subject} {description}", category)
    norm_priority = ticket_copilot_service.infer_priority(f"{subject} {description}", priority)

    summary = f"Tạo ticket mới: {subject} ({norm_priority})"
    params = {
        "subject": subject,
        "description": description,
        "priority": norm_priority,
        "category": norm_category,
        "customer_email": customer_email,
        "customer_name": customer_name,
        "workspace_id": workspace_id,
    }
    pending = registry.create_pending_action(
        action_type="create_escalation_ticket",
        summary=summary,
        parameters=params,
        creator_id=creator_id,
        creator_email=creator_email or customer_email,
    )
    response_text = (
        f"Tôi đã chuẩn bị yêu cầu tạo phiếu hỗ trợ (ticket) mới cho bạn:\n"
        f"- **Tiêu đề**: {subject}\n"
        f"- **Danh mục**: {norm_category}\n"
        f"- **Mức độ ưu tiên**: {norm_priority} (Cam kết SLA: {ticket_copilot_service.SLA_MAP.get(norm_priority, 8)} giờ)\n\n"
        f"Vì thao tác này sẽ ghi dữ liệu mới vào hệ thống, vui lòng bấm **Xác nhận** ở thẻ bên dưới để hoàn tất tạo ticket."
    )
    return {
        "response": response_text,
        "pending_action": pending,
    }


async def handle_prepare_ticket_update(
    registry: AgentToolRegistry,
    ticket_code: str,
    priority: Optional[str] = None,
    status: Optional[str] = None,
    creator_id: Optional[int] = None,
    creator_email: Optional[str] = None,
) -> Dict[str, Any]:
    """Tool 4: Mutating tool that prepares a PendingAction to update a ticket's priority or status (requires user confirmation)."""
    formatted_code = ticket_code.upper() if ticket_code.startswith("#") else f"#{ticket_code.upper()}"
    changes = []
    params: Dict[str, Any] = {"ticket_code": formatted_code}
    if priority:
        params["priority"] = priority.capitalize()
        changes.append(f"Ưu tiên -> {priority.capitalize()}")
    if status:
        params["status"] = status.lower()
        changes.append(f"Trạng thái -> {status.lower()}")

    change_str = ", ".join(changes) if changes else "Ưu tiên -> Urgent"
    if not priority and not status:
        params["priority"] = "Urgent"

    summary = f"Cập nhật ticket {formatted_code}: {change_str}"
    pending = registry.create_pending_action(
        action_type="update_ticket_priority_or_status",
        summary=summary,
        parameters=params,
        creator_id=creator_id,
        creator_email=creator_email,
    )
    response_text = (
        f"Tôi đã chuẩn bị lệnh cập nhật cho phiếu hỗ trợ **{formatted_code}** ({change_str}).\n"
        f"Vui lòng bấm **Xác nhận** bên dưới để áp dụng thay đổi vào cơ sở dữ liệu."
    )
    return {
        "response": response_text,
        "pending_action": pending,
    }


def register_default_tools(registry: AgentToolRegistry) -> None:
    """Registers the 4 canonical SmartDesk AI support tools (Capability B - REQ-14)."""
    registry.register(
        ToolDefinition(
            name="lookup_customer_tickets",
            description="Tra cứu trạng thái phiếu hỗ trợ (ticket) của khách hàng theo mã #TICK-XXXX hoặc email.",
            parameters_schema={
                "type": "object",
                "properties": {
                    "ticket_code": {"type": "string", "description": "Mã ticket dạng #TICK-1042"},
                    "customer_email": {"type": "string", "description": "Email của khách hàng"},
                },
            },
            requires_confirmation=False,
            handler=handle_lookup_customer_tickets,
        )
    )
    registry.register(
        ToolDefinition(
            name="search_workspace_knowledge",
            description="Tìm kiếm nhanh quy định và chính sách trong kho tri thức của Workspace hiện tại.",
            parameters_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Từ khóa cần tra cứu"},
                    "workspace_id": {"type": "integer", "description": "ID của Workspace"},
                },
                "required": ["query"],
            },
            requires_confirmation=False,
            handler=handle_search_workspace_knowledge,
        )
    )
    registry.register(
        ToolDefinition(
            name="create_escalation_ticket",
            description="Tạo phiếu hỗ trợ kỹ thuật mới (ticket) khi khách hàng yêu cầu. Cần xác nhận từ người dùng trước khi lưu DB.",
            parameters_schema={
                "type": "object",
                "properties": {
                    "subject": {"type": "string", "description": "Tiêu đề sự cố"},
                    "description": {"type": "string", "description": "Mô tả chi tiết sự cố"},
                    "priority": {"type": "string", "enum": ["Low", "Medium", "High", "Urgent"]},
                    "category": {"type": "string", "enum": ["Authentication", "Billing", "Bug Report", "Feature Request", "General"]},
                },
                "required": ["subject", "description"],
            },
            requires_confirmation=True,
        )
    )
    registry.register(
        ToolDefinition(
            name="update_ticket_priority_or_status",
            description="Cập nhật mức độ ưu tiên (priority) hoặc trạng thái (status) của một ticket hiện có. Cần xác nhận trước khi lưu DB.",
            parameters_schema={
                "type": "object",
                "properties": {
                    "ticket_code": {"type": "string", "description": "Mã ticket dạng #TICK-1042"},
                    "priority": {"type": "string", "enum": ["Low", "Medium", "High", "Urgent"]},
                    "status": {"type": "string", "enum": ["open", "in_progress", "resolved"]},
                },
                "required": ["ticket_code"],
            },
            requires_confirmation=True,
        )
    )


async def detect_and_route_tool(
    query: str,
    session: Optional[AsyncSession] = None,
    workspace_id: int = 1,
    registry: Optional[AgentToolRegistry] = None,
    current_user: Optional[Any] = None,
) -> Optional[Dict[str, Any]]:
    """
    Single-pass deterministic + intent tool router for Chat & Streaming endpoints.
    Returns None if the query is a normal RAG knowledge question.
    """
    active_registry = registry or agent_tool_registry
    q_low = query.lower().strip()

    # Extract #TICK-XXXX or email if present
    tick_match = re.search(r"#?tick-\d{3,6}", q_low, re.IGNORECASE)
    ticket_code = tick_match.group(0).upper() if tick_match else None
    if ticket_code and not ticket_code.startswith("#"):
        ticket_code = f"#{ticket_code}"

    email_match = re.search(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", query)
    customer_email = email_match.group(0) if email_match else None

    # 1. Check for Mutating Intent: Update existing ticket priority or status
    update_patterns = [
        r"(cập\s+nhật|đổi|thay\s+đổi|nâng|chuyển|update)\s+.*(ticket|phiếu|#?tick-\d+)",
        r"(đóng|giải\s+quyết|resolve)\s+(ticket|phiếu)\s+#?tick-\d+",
    ]
    if any(re.search(p, q_low) for p in update_patterns) and ticket_code:
        # Decision Option A: Enforce authorization at prepare time
        user_role = _get_user_attr(current_user, "role", None)
        if user_role != "admin":
            refusal_msg = (
                "Chỉ Quản trị viên (Admin) hoặc Nhân viên hỗ trợ mới có quyền cập nhật trạng thái "
                "hoặc mức độ ưu tiên của phiếu hỗ trợ qua hệ thống tự động. "
                "Nếu quý khách cần thay đổi thông tin phiếu, vui lòng liên hệ trực tiếp với bộ phận chăm sóc khách hàng để được hỗ trợ."
            )
            return {
                "tools_called": ["update_ticket_priority_or_status"],
                "response": refusal_msg,
                "pending_action": None,
                "confidence": 0.95,
            }

        new_prio: Optional[str] = None
        for p_level in ["urgent", "high", "medium", "low"]:
            if p_level in q_low:
                new_prio = p_level.capitalize()
                break
        if not new_prio and ("khẩn cấp" in q_low or "gấp" in q_low):
            new_prio = "Urgent"

        new_status: Optional[str] = None
        if "resolved" in q_low or "đóng" in q_low or "giải quyết" in q_low:
            new_status = "resolved"
        elif "in_progress" in q_low or "đang xử lý" in q_low:
            new_status = "in_progress"

        prep = await handle_prepare_ticket_update(
            registry=active_registry,
            ticket_code=ticket_code,
            priority=new_prio,
            status=new_status,
            creator_id=_get_user_attr(current_user, "id", None),
            creator_email=_get_user_attr(current_user, "email", None),
        )
        return {
            "tools_called": ["update_ticket_priority_or_status"],
            "response": prep["response"],
            "pending_action": prep["pending_action"],
            "confidence": 0.95,
        }

    # 2. Check for Mutating Intent: Create escalation ticket
    create_patterns = [
        r"(tạo|lập|mở|gửi|create)\s+(giúp\s+)?(tôi\s+|mình\s+)?(một\s+)?(ticket|phiếu\s+hỗ\s+trợ)",
        r"(ticket|phiếu\s+hỗ\s+trợ)\s+mới",
    ]
    if any(re.search(p, q_low) for p in create_patterns):
        prio = "Medium"
        for p_level in ["urgent", "high", "medium", "low"]:
            if p_level in q_low:
                prio = p_level.capitalize()
                break
        if "khẩn cấp" in q_low:
            prio = "Urgent"

        cleaned_subj = re.sub(
            r"^(hãy\s+|vui\s+lòng\s+)?(tạo|lập|mở|gửi|create)\s+(giúp\s+)?(tôi\s+|mình\s+)?(một\s+)?(ticket|phiếu\s+hỗ\s+trợ)\s*(về\s+|cho\s+)?",
            "",
            query.strip(),
            flags=re.IGNORECASE,
        ).strip()
        subject = cleaned_subj[:120] if len(cleaned_subj) >= 5 else "Yêu cầu hỗ trợ kỹ thuật khẩn cấp"
        description = f"Khách hàng yêu cầu tạo ticket qua AI Chat: {query.strip()}"

        user_email = customer_email or (_get_user_attr(current_user, "email", None) if current_user else "an.nguyen@company.vn")
        user_name = _get_user_attr(current_user, "full_name", "Nguyễn Văn An") if current_user else "Nguyễn Văn An"
        c_id = _get_user_attr(current_user, "id", None) if current_user else None
        c_email = _get_user_attr(current_user, "email", None) if current_user else None

        prep = await handle_prepare_escalation_ticket(
            registry=active_registry,
            subject=subject,
            description=description,
            priority=prio,
            category=ticket_copilot_service.infer_category(query),
            customer_email=user_email,
            customer_name=user_name,
            workspace_id=workspace_id,
            creator_id=c_id,
            creator_email=c_email,
        )
        return {
            "tools_called": ["create_escalation_ticket"],
            "response": prep["response"],
            "pending_action": prep["pending_action"],
            "confidence": 0.95,
        }

    # 3. Check for Read-Only Intent: Lookup customer ticket status
    lookup_patterns = [
        r"(kiểm\s+tra|tra\s+cứu|xem|tình\s+trạng|trạng\s+thái|lookup|check)\s+.*(ticket|phiếu\s+hỗ\s+trợ|#?tick-\d+)",
        r"#tick-\d{3,6}",
    ]
    if any(re.search(p, q_low) for p in lookup_patterns):
        lookup_res = await handle_lookup_customer_tickets(
            session=session,
            customer_email=customer_email,
            ticket_code=ticket_code,
            workspace_id=workspace_id,
            current_user=current_user,
        )
        return {
            "tools_called": ["lookup_customer_tickets"],
            "response": lookup_res["message"],
            "pending_action": None,
            "confidence": 0.94 if lookup_res["found"] else 0.70,
        }

    return None


agent_tool_registry = AgentToolRegistry()
register_default_tools(agent_tool_registry)
