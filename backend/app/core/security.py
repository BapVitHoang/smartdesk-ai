"""Security utilities: input sanitization, prompt injection defense, PII masking, and authentication primitives."""

import asyncio
import base64
import hashlib
import hmac
import logging
import os
import re
import time
from collections import defaultdict, deque
from typing import Any, Deque, Dict, Optional, Tuple

from app.core.config import is_placeholder_secret, settings

logger = logging.getLogger("smartdesk.security")

# Common prompt injection signatures and malicious jailbreak patterns (English and Vietnamese)
PROMPT_INJECTION_PATTERNS = [
    # English patterns
    r"ignore\s+(all\s+)?(previous|prior)\s+instructions?",
    r"disregard\s+(all\s+)?(previous|prior)\s+instructions?",
    r"you\s+are\s+now\s+(in\s+)?developer\s+mode",
    r"system\s+prompt\s*(override|reveal|leak|bypass)",
    r"<\|system\|>",
    r"\[system\]",
    r"dan\s+mode",
    r"bypass\s+all\s+filters?",
    r"reveal\s+your\s+instructions?",
    r"repeat\s+everything\s+above",
    r"output\s+the\s+system\s+prompt",
    # Vietnamese patterns
    r"bỏ\s+qua\s+(tất\s+cả\s+|mọi\s+|các\s+)?(hướng\s+dẫn|chỉ\s+dẫn|quy\s+tắc|lệnh)",
    r"(tiết\s+lộ|in\s+ra|hiển\s+thị|cho\s+tôi\s+xem)\s+.*(system\s+prompt|hướng\s+dẫn\s+hệ\s+thống|cấu\s+hình\s+gốc)",
    r"chế\s+độ\s+(nhà\s+phát\s+triển|developer|không\s+giới\s+hạn|dan)",
    r"quên\s+(hết\s+|tất\s+cả\s+)?(những\s+gì|hướng\s+dẫn|quy\s+tắc)",
]

COMPILED_INJECTION_REGEX = [
    re.compile(pattern, re.IGNORECASE) for pattern in PROMPT_INJECTION_PATTERNS
]


def sanitize_input(text: str, max_length: int = 4000) -> str:
    """
    Sanitizes user input by stripping harmful control characters and truncating excessive lengths.
    """
    if not text:
        return ""

    # Strip null bytes and non-printable control characters (except newline, tab, carriage return)
    cleaned = "".join(ch for ch in text if ch.isprintable() or ch in "\n\r\t")

    # Truncate if exceeds max length
    if len(cleaned) > max_length:
        cleaned = cleaned[:max_length]

    return cleaned.strip()


def check_prompt_injection(text: str) -> Tuple[bool, str]:
    """
    Scans the provided text against known prompt injection and jailbreak signatures.

    Returns:
        Tuple[bool, str]: (is_suspicious, matched_pattern_or_reason)
    """
    if not text:
        return False, ""

    for regex in COMPILED_INJECTION_REGEX:
        match = regex.search(text)
        if match:
            return True, f"Suspicious prompt token detected: '{match.group(0)}'"

    return False, ""


def redact_pii(text: str) -> str:
    """
    Masks sensitive personal identifiable information (PII) before external LLM calls.
    Masks emails, phone numbers, and CCCD/card numbers while preserving monetary prices and ticket codes.
    """
    if not text:
        return ""

    # 1. Mask Email addresses
    redacted = re.sub(
        r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
        "[REDACTED_EMAIL]",
        text
    )

    # 2. Mask 10-digit Vietnamese phone numbers (+84... or 03/05/07/08/09...)
    redacted = re.sub(
        r"(?:\+84|0)[35789]\d{8}\b",
        "[REDACTED_PHONE]",
        redacted
    )

    # 3. Mask 16-digit credit cards or 12-digit Vietnamese CCCD (while NOT touching prices like 25.000.000 VNĐ)
    redacted = re.sub(
        r"\b\d{4}[ -]\d{4}[ -]\d{4}[ -]\d{4}\b",
        "[REDACTED_ID]",
        redacted
    )
    redacted = re.sub(
        r"(?<![\d.,])\b\d{12}\b(?![\d.,])",
        "[REDACTED_ID]",
        redacted
    )

    return redacted


# ---------------------------------------------------------------------------
# Authentication primitives (REQ-06, REQ-09, REQ-36)
# ---------------------------------------------------------------------------

# scrypt parameters (OWASP-recommended minimum: N=2^15 for interactive; 2^14 keeps demo logins fast).
_SCRYPT_N: int = 2**14
_SCRYPT_R: int = 8
_SCRYPT_P: int = 1
_SCRYPT_DKLEN: int = 32
_SCRYPT_MAXMEM: int = 64 * 1024 * 1024


def hash_password(password: str) -> str:
    """Hashes a password with a random 16-byte salt using hashlib.scrypt. Format: scrypt$N$r$p$salt$hash."""
    salt = os.urandom(16)
    digest = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=_SCRYPT_N,
        r=_SCRYPT_R,
        p=_SCRYPT_P,
        dklen=_SCRYPT_DKLEN,
        maxmem=_SCRYPT_MAXMEM,
    )
    return "scrypt${}${}${}${}${}".format(
        _SCRYPT_N,
        _SCRYPT_R,
        _SCRYPT_P,
        base64.b64encode(salt).decode("ascii"),
        base64.b64encode(digest).decode("ascii"),
    )


def verify_password(password: str, stored_hash: Optional[str]) -> bool:
    """Constant-time password verification against a stored scrypt hash. Returns False for malformed hashes."""
    if not stored_hash:
        return False
    try:
        scheme, n_s, r_s, p_s, salt_b64, hash_b64 = stored_hash.split("$")
        if scheme != "scrypt":
            return False
        salt = base64.b64decode(salt_b64)
        expected = base64.b64decode(hash_b64)
        candidate = hashlib.scrypt(
            password.encode("utf-8"),
            salt=salt,
            n=int(n_s),
            r=int(r_s),
            p=int(p_s),
            dklen=len(expected),
            maxmem=_SCRYPT_MAXMEM,
        )
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(candidate, expected)


# Verified against when the account does not exist, so response time does not reveal valid emails.
_DUMMY_PASSWORD_HASH: str = hash_password(base64.b64encode(os.urandom(12)).decode("ascii"))


async def verify_password_async(password: str, stored_hash: Optional[str]) -> bool:
    """Runs scrypt verification in a worker thread. A dummy hash is checked when no hash exists (timing parity)."""
    return await asyncio.to_thread(verify_password, password, stored_hash or _DUMMY_PASSWORD_HASH) and bool(stored_hash)


class LoginThrottle:
    """Simple in-memory sliding-window throttle for failed login attempts (per email and per client IP)."""

    def __init__(self) -> None:
        self._failures: Dict[str, Deque[float]] = defaultdict(deque)

    def _prune(self, key: str, now: float) -> Deque[float]:
        window = float(settings.LOGIN_THROTTLE_WINDOW_SECONDS)
        bucket = self._failures[key]
        while bucket and now - bucket[0] > window:
            bucket.popleft()
        if not bucket:
            self._failures.pop(key, None)
            return deque()
        return bucket

    def is_blocked(self, *keys: str) -> bool:
        """Returns True if any key has reached the maximum number of failed attempts within the window."""
        now = time.monotonic()
        limit = settings.LOGIN_MAX_FAILED_ATTEMPTS
        return any(len(self._prune(k, now)) >= limit for k in keys if k)

    def record_failure(self, *keys: str) -> None:
        """Records one failed attempt for every non-empty key."""
        now = time.monotonic()
        for k in keys:
            if k:
                self._prune(k, now)
                self._failures[k].append(now)

    def reset(self, *keys: str) -> None:
        """Clears failures for the given keys (called after a successful login)."""
        for k in keys:
            self._failures.pop(k, None)

    def clear_all(self) -> None:
        """Clears every recorded failure (used by tests)."""
        self._failures.clear()


login_throttle = LoginThrottle()


class GoogleAuthError(Exception):
    """Raised when a Google ID token cannot be verified. `status_code` maps to the HTTP response."""

    def __init__(self, message: str, status_code: int = 401) -> None:
        super().__init__(message)
        self.status_code = status_code


_GOOGLE_ISSUERS = ("accounts.google.com", "https://accounts.google.com")


def _verify_google_token_sync(credential: str, client_id: str) -> Dict[str, Any]:
    """Blocking verification: signature (Google certs), audience, issuer and expiry via google-auth."""
    from google.auth.transport import requests as google_requests
    from google.oauth2 import id_token as google_id_token

    return google_id_token.verify_oauth2_token(credential, google_requests.Request(), audience=client_id)


async def verify_google_credential(credential: str) -> Dict[str, Any]:
    """
    Verifies a Google ID token and returns its claims.
    Raises GoogleAuthError(501) when GOOGLE_OAUTH_CLIENT_ID is not configured (never accepts unverified tokens),
    and GoogleAuthError(401) for any invalid token (garbled, unsigned, wrong audience, expired, unverified email).
    """
    client_id = settings.GOOGLE_OAUTH_CLIENT_ID.strip()
    if not client_id:
        raise GoogleAuthError("Google sign-in is not configured on this server.", status_code=501)
    if not credential or len(credential) > 4096:
        raise GoogleAuthError("Invalid Google credential.")

    try:
        claims = await asyncio.to_thread(_verify_google_token_sync, credential, client_id)
    except Exception as exc:  # google-auth raises ValueError / GoogleAuthError / transport errors
        logger.warning("Google ID token rejected: %s", type(exc).__name__)
        raise GoogleAuthError("Invalid Google credential.") from exc

    if claims.get("iss") not in _GOOGLE_ISSUERS:
        raise GoogleAuthError("Invalid Google credential.")
    if claims.get("aud") != client_id:
        raise GoogleAuthError("Invalid Google credential.")
    if claims.get("email_verified") is not True:
        raise GoogleAuthError("Google account email is not verified.")
    if not claims.get("email"):
        raise GoogleAuthError("Invalid Google credential.")
    return claims


def validate_auth_configuration() -> None:
    """
    Startup guard for the JWT secret.
    - Empty/whitespace or the old publicly known default value while DEMO_LOGIN_ENABLED is false: refuse to start
      (RuntimeError), so the application never serves tokens signed with a public or missing secret.
    - Secret generated at startup (Settings replaces a placeholder when demo login is enabled): log ONE warning,
      without the secret, that tokens become invalid after a restart and differ between worker processes.
    """
    if is_placeholder_secret(settings.JWT_SECRET_KEY):
        raise RuntimeError(
            "JWT_SECRET_KEY is empty or still the known default while DEMO_LOGIN_ENABLED is false. "
            "Set a strong JWT_SECRET_KEY (>= 32 random characters) before starting the server."
        )
    if settings.jwt_secret_is_ephemeral:
        logger.warning(
            "JWT_SECRET_KEY is not configured: a random per-process secret was generated. "
            "All issued tokens become invalid after a restart and are not shared between worker processes. "
            "Set JWT_SECRET_KEY in the environment for a stable secret."
        )
    elif len(settings.JWT_SECRET_KEY) < 32:
        logger.error("SECURITY WARNING: JWT_SECRET_KEY is shorter than 32 characters.")
