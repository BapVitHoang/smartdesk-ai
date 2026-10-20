"""Agent Tool Registry & Execution Interface (Extension Point for Owner 1 / REQ-15)."""

from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Dict, List, Optional


ToolHandler = Callable[..., Awaitable[Dict[str, Any]]]


@dataclass
class ToolDefinition:
    """Metadata and async handler for a callable support agent tool."""

    name: str
    description: str
    parameters_schema: Dict[str, Any] = field(default_factory=dict)
    requires_confirmation: bool = False
    handler: Optional[ToolHandler] = None


class AgentToolRegistry:
    """Central registry for support agent tools (lookup ticket, calculate SLA, escalate)."""

    def __init__(self) -> None:
        self._tools: Dict[str, ToolDefinition] = {}

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


agent_tool_registry = AgentToolRegistry()
