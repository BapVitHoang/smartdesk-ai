"""Application configuration settings module using Pydantic Settings."""

from typing import List, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
import json
import os
from pathlib import Path


class Settings(BaseSettings):
    """Centralized application configuration."""

    # Project Information
    PROJECT_NAME: str = "SmartDesk AI - Customer Support & Knowledge Synthesizer"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    DEBUG: bool = False

    # AI & Google Gemini Model Parameters
    GEMINI_API_KEY: str = ""
    LLM_MODEL_NAME: str = "gemini-1.5-flash"
    EMBEDDING_MODEL_NAME: str = "text-embedding-004"

    # Circuit Breaker & Strict Latency Budget (Max 4.0s)
    LLM_TIMEOUT_SECONDS: float = 4.0
    RAG_CONFIDENCE_THRESHOLD: float = 0.65

    # Database Configuration (PostgreSQL 16 with pgvector or SQLite async fallback)
    DATABASE_URL: str = "sqlite+aiosqlite:///./smartdesk.db"
    FALLBACK_SQLITE_URL: str = "sqlite+aiosqlite:///./smartdesk.db"

    # CORS Allowed Origins
    CORS_ORIGINS: Union[List[str], str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "*"
    ]

    # Seed FAQ File Path
    SEED_FAQ_PATH: str = "data/seed_faq.json"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True
    )

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
        
        # Check relative to this file's parent directories
        backend_root = Path(__file__).resolve().parent.parent.parent
        resolved = backend_root / self.SEED_FAQ_PATH
        if resolved.exists():
            return resolved
            
        return direct_path


settings = Settings()
