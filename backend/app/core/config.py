"""Application configuration settings module using Pydantic Settings."""

from typing import Any, List, Union
from pydantic import PrivateAttr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
import hashlib
import json
import secrets
from pathlib import Path


BACKEND_DIR: Path = Path(__file__).resolve().parent.parent.parent
PROJECT_ROOT: Path = BACKEND_DIR.parent
DEFAULT_SQLITE_PATH: str = (BACKEND_DIR / "smartdesk.db").as_posix()
# SHA-256 of the placeholder JWT secret that used to be published in the repository. The literal is intentionally
# NOT stored in code: any secret that is empty or hashes to this value is treated as "not configured".
KNOWN_DEFAULT_JWT_SECRET_SHA256: str = "ac5ca707a1e2e37c7ee4ba316972dae3f391fc9c4df01e5a205303f274c94263"


def is_placeholder_secret(secret: str) -> bool:
    """Returns True if the secret is empty/whitespace or equals the old publicly known default value."""
    cleaned = (secret or "").strip()
    if not cleaned:
        return True
    return hashlib.sha256(cleaned.encode("utf-8")).hexdigest() == KNOWN_DEFAULT_JWT_SECRET_SHA256


class Settings(BaseSettings):
    """Centralized application configuration."""

    # Project Information
    PROJECT_NAME: str = "SmartDesk AI - Customer Support & Knowledge Synthesizer"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    DEBUG: bool = False

    # AI Provider: "gemini" | "ollama"
    # Primary Cloud LLM (GA Google Gemini 3.5 Flash Lite)
    AI_PROVIDER: str = "gemini"
    GEMINI_API_KEY: str = ""
    LLM_MODEL_NAME: str = "gemini-3.5-flash-lite"
    LLM_FALLBACK_MODEL: str = ""
    LLM_FALLBACK_MODEL_NAME: str = "gemini-2.5-flash-lite"
    EMBEDDING_MODEL_NAME: str = "gemini-embedding-001"
    EMBEDDING_DIMENSIONS: int = 768

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
    # Empty = not configured. With DEMO_LOGIN_ENABLED=true a random per-process secret is generated at startup;
    # with DEMO_LOGIN_ENABLED=false the server refuses to start (see core.security.validate_auth_configuration).
    JWT_SECRET_KEY: str = ""
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24
    GOOGLE_OAUTH_CLIENT_ID: str = ""
    # Comma-separated (or JSON list) of emails allowed to hold the admin role when signing in via Google.
    ADMIN_EMAILS: Union[List[str], str] = []
    # One-click demo login for the seeded demo accounts only (LOCAL DEMO ONLY; disable in production).
    DEMO_LOGIN_ENABLED: bool = True
    # Demo-only default passwords for the seeded accounts. Override via environment for any shared deployment.
    DEMO_ADMIN_PASSWORD: str = "Admin@SmartDesk2026"
    DEMO_USER_PASSWORD: str = "User@SmartDesk2026"
    # In-memory login throttle (failed attempts per key within the window).
    LOGIN_MAX_FAILED_ATTEMPTS: int = 10
    LOGIN_THROTTLE_WINDOW_SECONDS: int = 60
    # Trusted proxy CIDRs for client IP resolution behind reverse proxies (Nginx / Docker).
    # Empty by default means trust only loopback (127.0.0.1/32, ::1/128).
    TRUSTED_PROXY_CIDRS: str = ""
    FORWARDED_ALLOW_IPS: str = ""

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

    _jwt_secret_ephemeral: bool = PrivateAttr(default=False)

    def model_post_init(self, __context: Any) -> None:
        """Replaces an empty/known-default JWT secret by a random per-process one when demo login is enabled."""
        super().model_post_init(__context)
        if is_placeholder_secret(self.JWT_SECRET_KEY) and self.DEMO_LOGIN_ENABLED:
            self.JWT_SECRET_KEY = secrets.token_urlsafe(48)
            self._jwt_secret_ephemeral = True

    @property
    def jwt_secret_is_ephemeral(self) -> bool:
        """True when JWT_SECRET_KEY was generated at startup (tokens become invalid after a restart)."""
        return self._jwt_secret_ephemeral

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

    @field_validator("ADMIN_EMAILS", mode="before")
    @classmethod
    def assemble_admin_emails(cls, v: Union[str, List[str]]) -> List[str]:
        """Parse ADMIN_EMAILS from a comma-separated string or JSON list into normalized lowercase emails."""
        items: List[str]
        if isinstance(v, str):
            v_stripped = v.strip()
            if v_stripped.startswith("[") and v_stripped.endswith("]"):
                try:
                    items = [str(i) for i in json.loads(v_stripped)]
                except Exception:
                    items = []
            else:
                items = v_stripped.split(",")
        elif isinstance(v, list):
            items = [str(i) for i in v]
        else:
            items = []
        return [i.strip().lower() for i in items if i and i.strip()]

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
