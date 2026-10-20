"""Application configuration settings module using Pydantic Settings."""

from typing import List, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
import json
from pathlib import Path


BACKEND_DIR: Path = Path(__file__).resolve().parent.parent.parent
PROJECT_ROOT: Path = BACKEND_DIR.parent
DEFAULT_SQLITE_PATH: str = (BACKEND_DIR / "smartdesk.db").as_posix()


class Settings(BaseSettings):
    """Centralized application configuration."""

    # Project Information
    PROJECT_NAME: str = "SmartDesk AI - Customer Support & Knowledge Synthesizer"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    DEBUG: bool = False

    # AI Provider: "gemini" | "ollama"
    AI_PROVIDER: str = "gemini"
    GEMINI_API_KEY: str = ""
    LLM_MODEL_NAME: str = "gemini-3.5-flash-lite"
    LLM_FALLBACK_MODEL_NAME: str = "gemini-2.5-flash-lite"
    EMBEDDING_MODEL_NAME: str = "gemini-embedding-001"

    # Local Ollama Settings
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_LLM_MODEL: str = "qwen2.5:3b"
    OLLAMA_EMBEDDING_MODEL: str = "nomic-embed-text"
    OLLAMA_TIMEOUT_SECONDS: float = 30.0
    OLLAMA_KEEP_ALIVE: str = "30m"

    # Circuit Breaker & Strict Latency Budget (Max 4.0s for Cloud Gemini)
    LLM_TIMEOUT_SECONDS: float = 4.0
    RAG_CONFIDENCE_THRESHOLD: float = 0.65

    # Database Configuration (PostgreSQL 16 with pgvector or SQLite async fallback)
    DATABASE_URL: str = f"sqlite+aiosqlite:///{DEFAULT_SQLITE_PATH}"
    FALLBACK_SQLITE_URL: str = f"sqlite+aiosqlite:///{DEFAULT_SQLITE_PATH}"

    # CORS Allowed Origins
    CORS_ORIGINS: Union[List[str], str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173"
    ]

    # Seed FAQ & Externalized Prompts Paths
    SEED_FAQ_PATH: str = (BACKEND_DIR / "data" / "seed_faq.json").as_posix()
    PROMPTS_PATH: str = (BACKEND_DIR / "data" / "prompts.json").as_posix()

    model_config = SettingsConfigDict(
        env_file=[
            str(PROJECT_ROOT / ".env"),
            str(BACKEND_DIR / ".env")
        ],
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True
    )

    @field_validator("DATABASE_URL", "FALLBACK_SQLITE_URL", mode="before")
    @classmethod
    def resolve_sqlite_path(cls, v: str) -> str:
        """Resolve relative SQLite paths to absolute paths within backend dir."""
        if isinstance(v, str):
            prefix = "sqlite+aiosqlite:///"
            if v.startswith(prefix):
                rel_path = v[len(prefix):]
                if rel_path.startswith("./"):
                    rel_path = rel_path[2:]
                path_obj = Path(rel_path)
                if not path_obj.is_absolute() and not (len(rel_path) > 1 and rel_path[1] == ":"):
                    abs_path = (BACKEND_DIR / rel_path).resolve().as_posix()
                    return f"{prefix}{abs_path}"
        return v

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        """Parse CORS_ORIGINS from string or JSON list."""
        if isinstance(v, str):
            v_stripped = v.strip()
            if v_stripped.startswith("[") and v_stripped.endswith("]"):
                try:
                    return json.loads(v_stripped)
                except Exception:
                    pass
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, list):
            return v
        return ["*"]

    @property
    def resolved_seed_faq_path(self) -> Path:
        """Resolve seed FAQ path relative to backend root."""
        direct_path = Path(self.SEED_FAQ_PATH)
        if direct_path.exists():
            return direct_path

        backend_root = Path(__file__).resolve().parent.parent.parent
        resolved = backend_root / self.SEED_FAQ_PATH
        if resolved.exists():
            return resolved

        return direct_path


settings = Settings()
