"""Versioned prompt catalog loader for SmartDesk AI (REQ-19 extension point)."""

import json
import logging
from pathlib import Path
from typing import Any, Dict

from app.core.config import BACKEND_DIR, settings

logger = logging.getLogger("smartdesk.prompts")

DEFAULT_PROMPTS: Dict[str, Dict[str, Any]] = {
    "rag_customer_support": {
        "version": "1.0.0",
        "temperature": 0.2,
        "template": (
            "You are {persona_name}, the official AI Support Assistant for '{workspace_name}' (Industry: {industry}).\n"
            "Tone of Voice: {tone_of_voice}\n"
            "Mandatory Business Rules:\n{business_rules}\n\n"
            "Strict Grounding Rules:\n"
            "1. Answer the customer's question truthfully using ONLY the provided Knowledge Base context.\n"
            "2. If the provided context does not contain enough information to answer truthfully, "
            "explicitly say you do not know and recommend escalating to a human support agent.\n"
            "3. Never hallucinate features, URLs, or policies not present in the context.\n"
            "4. Cite sources in your response when referencing specific articles using the format [Doc #ID: Title]."
        ),
    }
}


class PromptRegistry:
    """Loads versioned prompt templates from backend/data/prompts.json with safe fallback."""

    def __init__(self) -> None:
        self._version: str = "1.0.0"
        self._templates: Dict[str, Dict[str, Any]] = dict(DEFAULT_PROMPTS)
        self.reload()

    def reload(self) -> None:
        """Reload prompt definitions from disk."""
        candidates = [
            Path(settings.PROMPTS_PATH),
            BACKEND_DIR / "data" / "prompts.json",
        ]
        for path in candidates:
            if path.exists():
                try:
                    data = json.loads(path.read_text(encoding="utf-8"))
                    self._version = data.get("version", "1.0.0")
                    loaded = data.get("templates", {})
                    if isinstance(loaded, dict):
                        self._templates.update(loaded)
                    return
                except Exception as exc:
                    logger.warning(f"Failed to load prompt catalog from {path}: {exc}")

    @property
    def version(self) -> str:
        """Return catalog version string."""
        return self._version

    def get_prompt_meta(self, key: str) -> Dict[str, Any]:
        """Return raw metadata and template for a given prompt key."""
        return self._templates.get(key, DEFAULT_PROMPTS["rag_customer_support"])

    def render(self, key: str, **kwargs: Any) -> str:
        """Render a named prompt template with safe keyword substitution."""
        entry = self.get_prompt_meta(key)
        template_str = str(entry.get("template", ""))
        try:
            return template_str.format(**kwargs)
        except KeyError:
            return template_str


prompt_registry = PromptRegistry()
