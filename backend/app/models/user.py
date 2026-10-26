"""User ORM Model for OAuth2 authentication and Role-Based Access Control (RBAC)."""

from datetime import datetime
from typing import Optional
from sqlalchemy import Boolean, String, Integer, DateTime, func, true
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class User(Base):
    """User account model for customers and support staff."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    role: Mapped[str] = mapped_column(String(32), default="user", index=True)  # "admin" | "user"
    oauth_provider: Mapped[str] = mapped_column(String(50), default="google")
    workspace_id: Mapped[int] = mapped_column(Integer, default=1)
    # Salted scrypt hash (never the plain password). NULL for accounts that sign in only via Google/demo.
    password_hash: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true(), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
