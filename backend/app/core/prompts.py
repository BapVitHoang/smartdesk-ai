"""Versioned prompt catalog loader with automatic hot-reload for SmartDesk AI (REQ-19, REQ-42)."""

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

from app.core.config import BACKEND_DIR, settings

logger = logging.getLogger("smartdesk.prompts")

DEFAULT_PROMPTS: Dict[str, Dict[str, Any]] = {
    "rag_customer_support": {
        "version": "2.1.0",
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
    """Loads versioned prompt templates from backend/data/prompts.json with hot-reload and safe fallback."""

    def __init__(self) -> None:
        self._version: str = "1.0.0"
        self._catalog_release: str = "v2.1"
        self._templates: Dict[str, Dict[str, Any]] = dict(DEFAULT_PROMPTS)
        self._last_mtime: float = 0.0
        self._active_path: Optional[Path] = None
        self.reload()

    def _check_hot_reload(self) -> None:
        """Automatically reloads prompts.json if the file was modified on disk (for Live Change Defense)."""
        if self._active_path and self._active_path.exists():
            try:
                current_mtime = self._active_path.stat().st_mtime
                if current_mtime > self._last_mtime:
                    self.reload()
            except Exception:
                pass

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
                    self._catalog_release = data.get("catalog_release", f"v{self._version}")
                    loaded = data.get("templates", {})
                    if isinstance(loaded, dict):
                        self._templates.update(loaded)
                    self._active_path = path
                    self._last_mtime = path.stat().st_mtime
                    return
                except Exception as exc:
                    logger.warning(f"Failed to load prompt catalog from {path}: {exc}")

    @property
    def version(self) -> str:
        """Return catalog version string."""
        self._check_hot_reload()
        return self._version

    def get_prompt_version(self, key: str) -> str:
        """Return formatted prompt key + version identifier for telemetry logging."""
        self._check_hot_reload()
        entry = self._templates.get(key, {})
        ver = entry.get("version", self._version)
        return f"{key}@v{ver}"

    def get_prompt_meta(self, key: str) -> Dict[str, Any]:
        """Return raw metadata and template for a given prompt key."""
        self._check_hot_reload()
        return self._templates.get(key, DEFAULT_PROMPTS["rag_customer_support"])

    def render(self, key: str, **kwargs: Any) -> str:
        """Render a named prompt template with safe keyword substitution."""
        entry = self.get_prompt_meta(key)
        template_str = str(entry.get("template", ""))
        try:
            return template_str.format(**kwargs)
        except KeyError as exc:
            logger.warning(f"Missing placeholder {exc} when rendering prompt '{key}'")
            return template_str


prompt_registry = PromptRegistry()
