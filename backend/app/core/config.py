"""Application configuration settings module using Pydantic Settings."""

from typing import List, Union, Optional
from pydantic import field_validator, model_validator
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
    ENVIRONMENT: str = "development"  # "development" | "production" | "test"

    # AI Provider: "gemini" | "ollama"
    # Primary Cloud LLM (GA Google Gemini 3.5 Flash Lite)
    AI_PROVIDER: str = "gemini"
    GEMINI_API_KEY: str = ""
    LLM_MODEL_NAME: str = "gemini-3.5-flash-lite"
    LLM_FALLBACK_MODEL: str = ""
    LLM_FALLBACK_MODEL_NAME: str = "gemini-2.5-flash-lite"
    EMBEDDING_MODEL_NAME: str = "gemini-embedding-001"

    # Token Pricing for REQ-22 Observability (GA Gemini 3.5 Flash Lite rates per 1M tokens)
    LLM_INPUT_COST_PER_MILLION: float = 0.30
    LLM_OUTPUT_COST_PER_MILLION: float = 2.50

    # Local Ollama Settings
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_LLM_MODEL: str = "qwen2.5:3b"
    OLLAMA_EMBEDDING_MODEL: str = "nomic-embed-text"
    OLLAMA_TIMEOUT_SECONDS: float = 30.0
    OLLAMA_KEEP_ALIVE: str = "30m"

    # Circuit Breaker & Strict Latency Budget (Max 4.0s for Cloud Gemini)
    LLM_TIMEOUT_SECONDS: float = 4.0
    RATE_LIMIT_COOLDOWN_SECONDS: int = 60
    RAG_CONFIDENCE_THRESHOLD: float = 0.65
    RAG_MIN_SIMILARITY_SCORE: float = 0.25

    # Document Chunking
    CHUNK_SIZE: int = 700
    CHUNK_OVERLAP: int = 100

    # Authentication & RBAC (Hybrid OAuth2 + Demo Login)
    JWT_SECRET_KEY: str = "smartdesk-secret-key-change-in-production-2026"
    JWT_SECRET: str = ""  # Backward-compatible env alias for JWT_SECRET_KEY
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_OAUTH_CLIENT_ID: str = ""  # Backward-compatible env alias for GOOGLE_CLIENT_ID
    ADMIN_EMAILS: Union[List[str], str] = ["admin@smartdesk.ai"]
    DEMO_LOGIN_ENABLED: bool = True
    DEV_AUTH_BYPASS: bool = False

    # Database Configuration (PostgreSQL 16 with pgvector or SQLite async fallback)
    DATABASE_URL: str = f"sqlite+aiosqlite:///{DEFAULT_SQLITE_PATH}"
    FALLBACK_SQLITE_URL: str = f"sqlite+aiosqlite:///{DEFAULT_SQLITE_PATH}"

    # CORS Allowed Origins
    ALLOWED_ORIGINS: Optional[Union[List[str], str]] = None
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

    @field_validator("DEBUG", mode="before")
    @classmethod
    def parse_debug(cls, v: object) -> bool:
        """Safely parse DEBUG from boolean or arbitrary string (e.g. 'release', 'false')."""
        if isinstance(v, bool):
            return v
        if isinstance(v, str):
            return v.strip().lower() in ("true", "1", "yes", "debug", "dev")
        return False

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

    @field_validator("ADMIN_EMAILS", mode="before")
    @classmethod
    def parse_admin_emails(cls, v: Union[str, List[str]]) -> List[str]:
        """Parse ADMIN_EMAILS into a normalized lowercase list."""
        if isinstance(v, str):
            v_stripped = v.strip()
            if v_stripped.startswith("[") and v_stripped.endswith("]"):
                try:
                    loaded = json.loads(v_stripped)
                    if isinstance(loaded, list):
                        return [str(e).strip().lower() for e in loaded if str(e).strip()]
                except Exception:
                    pass
            return [e.strip().lower() for e in v.split(",") if e.strip()]
        elif isinstance(v, list):
            return [str(e).strip().lower() for e in v if str(e).strip()]
        return ["admin@smartdesk.ai"]

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

    @model_validator(mode="after")
    def reconcile_aliases(self) -> "Settings":
        """Reconcile environment variable aliases."""
        if self.JWT_SECRET and not self.JWT_SECRET_KEY:
            self.JWT_SECRET_KEY = self.JWT_SECRET
        elif self.JWT_SECRET and self.JWT_SECRET_KEY == "smartdesk-secret-key-change-in-production-2026":
            self.JWT_SECRET_KEY = self.JWT_SECRET

        if self.GOOGLE_CLIENT_ID and not self.GOOGLE_OAUTH_CLIENT_ID:
            self.GOOGLE_OAUTH_CLIENT_ID = self.GOOGLE_CLIENT_ID
        elif self.GOOGLE_OAUTH_CLIENT_ID and not self.GOOGLE_CLIENT_ID:
            self.GOOGLE_CLIENT_ID = self.GOOGLE_OAUTH_CLIENT_ID

        if self.ALLOWED_ORIGINS:
            if isinstance(self.ALLOWED_ORIGINS, str):
                origins = [i.strip() for i in self.ALLOWED_ORIGINS.split(",") if i.strip()]
            else:
                origins = list(self.ALLOWED_ORIGINS)
            if origins:
                self.CORS_ORIGINS = origins

        return self

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
