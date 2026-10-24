"""JWT secret handling tests (REQ-06, REQ-09, REQ-36). Offline, no network.

They build their own Settings objects with `_env_file=None` and explicit kwargs, so the result never depends on a
developer's local backend/.env or environment variables.
"""

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import jwt
import pytest
from httpx import AsyncClient

from app.core import security
from app.core.config import KNOWN_DEFAULT_JWT_SECRET_SHA256, Settings, is_placeholder_secret, settings

# The old, publicly known default. It may appear ONLY in this test module, to prove that it is rejected.
OLD_DEFAULT_SECRET = "smartdesk-secret-key-change-in-production-2026"
CONFIGURED_SECRET = "unit-test-configured-secret-value-0123456789-abcdef"
BACKEND_DIR = Path(__file__).resolve().parents[2]


def _fresh_settings(**overrides) -> Settings:
    """Settings that ignore .env files and the process environment for the fields given explicitly."""
    return Settings(_env_file=None, **overrides)


def _token_signed_with(secret: str) -> str:
    now = datetime.now(timezone.utc)
    return jwt.encode(
        {"sub": "admin@smartdesk.ai", "role": "admin", "exp": now + timedelta(hours=1), "iat": now},
        secret,
        algorithm="HS256",
    )


@pytest.mark.parametrize("placeholder", ["", "   ", OLD_DEFAULT_SECRET, f"  {OLD_DEFAULT_SECRET}  "])
def test_placeholder_detection(placeholder: str) -> None:
    assert is_placeholder_secret(placeholder) is True
    assert is_placeholder_secret(CONFIGURED_SECRET) is False


def test_old_default_literal_is_not_stored_in_application_code() -> None:
    """The application only keeps the SHA-256 of the old default, never the literal."""
    app_dir = BACKEND_DIR / "app"
    offenders = [
        str(p.relative_to(BACKEND_DIR))
        for p in app_dir.rglob("*.py")
        if OLD_DEFAULT_SECRET in p.read_text(encoding="utf-8")
    ]
    assert offenders == []
    assert hashlib.sha256(OLD_DEFAULT_SECRET.encode()).hexdigest() == KNOWN_DEFAULT_JWT_SECRET_SHA256


@pytest.mark.asyncio
async def test_token_signed_with_old_default_is_rejected_and_configured_secret_is_accepted(
    unauth_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Even when the environment still carries the old default, the running secret is NOT the old default."""
    # A deployment (or an old .env copied from .env.example) that still sets the published default value.
    from_old_env = _fresh_settings(JWT_SECRET_KEY=OLD_DEFAULT_SECRET, DEMO_LOGIN_ENABLED=True)
    assert from_old_env.JWT_SECRET_KEY != OLD_DEFAULT_SECRET
    monkeypatch.setattr(settings, "JWT_SECRET_KEY", from_old_env.JWT_SECRET_KEY)

    forged = _token_signed_with(OLD_DEFAULT_SECRET)
    res_forged = await unauth_client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {forged}"})
    assert res_forged.status_code == 401

    # A deployment with a properly configured secret keeps using exactly that value and accepts tokens signed with it.
    configured = _fresh_settings(JWT_SECRET_KEY=CONFIGURED_SECRET, DEMO_LOGIN_ENABLED=True)
    assert configured.JWT_SECRET_KEY == CONFIGURED_SECRET
    assert configured.jwt_secret_is_ephemeral is False
    monkeypatch.setattr(settings, "JWT_SECRET_KEY", configured.JWT_SECRET_KEY)

    good = _token_signed_with(CONFIGURED_SECRET)
    res_good = await unauth_client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {good}"})
    assert res_good.status_code == 200
    assert res_good.json()["email"] == "admin@smartdesk.ai"

    # ...and now the old default is rejected under the configured secret too.
    res_old = await unauth_client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {_token_signed_with(OLD_DEFAULT_SECRET)}"}
    )
    assert res_old.status_code == 401


@pytest.mark.parametrize("unconfigured", ["", "   ", OLD_DEFAULT_SECRET])
def test_unconfigured_secret_becomes_random_per_instance(unconfigured: str) -> None:
    first = _fresh_settings(JWT_SECRET_KEY=unconfigured, DEMO_LOGIN_ENABLED=True)
    second = _fresh_settings(JWT_SECRET_KEY=unconfigured, DEMO_LOGIN_ENABLED=True)
    for s in (first, second):
        assert len(s.JWT_SECRET_KEY) >= 43
        assert is_placeholder_secret(s.JWT_SECRET_KEY) is False
        assert s.jwt_secret_is_ephemeral is True
    assert first.JWT_SECRET_KEY != second.JWT_SECRET_KEY


def test_two_separate_process_starts_get_different_secrets() -> None:
    """Two fresh interpreters (no secret configured) must not share a secret. Only SHA-256 prefixes are printed."""
    code = (
        "import hashlib, json;"
        "from app.core.config import Settings;"
        "s = Settings(_env_file=None, JWT_SECRET_KEY='', DEMO_LOGIN_ENABLED=True);"
        "print(json.dumps({'len': len(s.JWT_SECRET_KEY), 'eph': s.jwt_secret_is_ephemeral,"
        " 'h': hashlib.sha256(s.JWT_SECRET_KEY.encode()).hexdigest()[:16]}))"
    )
    outputs = []
    for _ in range(2):
        proc = subprocess.run(
            [sys.executable, "-c", code], cwd=str(BACKEND_DIR), capture_output=True, text=True, timeout=60
        )
        assert proc.returncode == 0, proc.stderr[-500:]
        outputs.append(json.loads(proc.stdout.strip().splitlines()[-1]))
    assert all(o["len"] >= 43 and o["eph"] is True for o in outputs)
    assert outputs[0]["h"] != outputs[1]["h"]


def test_demo_off_with_unconfigured_secret_refuses_to_start(monkeypatch: pytest.MonkeyPatch) -> None:
    for unconfigured in ("", OLD_DEFAULT_SECRET):
        strict = _fresh_settings(JWT_SECRET_KEY=unconfigured, DEMO_LOGIN_ENABLED=False)
        assert is_placeholder_secret(strict.JWT_SECRET_KEY) is True
        assert strict.jwt_secret_is_ephemeral is False
        monkeypatch.setattr(security, "settings", strict)
        with pytest.raises(RuntimeError):
            security.validate_auth_configuration()


def test_demo_off_with_configured_secret_starts(monkeypatch: pytest.MonkeyPatch) -> None:
    strict = _fresh_settings(JWT_SECRET_KEY=CONFIGURED_SECRET, DEMO_LOGIN_ENABLED=False)
    monkeypatch.setattr(security, "settings", strict)
    security.validate_auth_configuration()  # must not raise


def test_ephemeral_secret_logs_one_warning_without_the_secret(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    demo = _fresh_settings(JWT_SECRET_KEY="", DEMO_LOGIN_ENABLED=True)
    monkeypatch.setattr(security, "settings", demo)
    with caplog.at_level("WARNING", logger="smartdesk.security"):
        security.validate_auth_configuration()
    warnings = [r for r in caplog.records if r.name == "smartdesk.security" and r.levelname == "WARNING"]
    assert len(warnings) == 1
    assert demo.JWT_SECRET_KEY not in warnings[0].getMessage()
