"""Offline tests for Gemini API key rotation in LLMService (no network)."""

from typing import Any, List

import pytest

from app.core.exceptions import LLMServiceException
from app.services.llm_service import LLMService


def _make_service(
    monkeypatch: pytest.MonkeyPatch, keys: List[str], failing: set
) -> tuple:
    calls: List[str] = []
    service = LLMService.__new__(LLMService)
    service.provider = "gemini"
    service.api_keys = keys
    service._key_index = 0
    service._key_blocked_until = {}
    service.api_key = keys[0]
    service.cooldown_until = 0.0
    service._client = object()
    service._sdk_type = "genai"

    monkeypatch.setattr(service, "_init_client", lambda: None)

    async def fake_once(
        prompt: str, system_prompt: str, temperature: float, response_schema: Any = None
    ) -> str:
        calls.append(service.api_key)
        if service.api_key in failing:
            raise RuntimeError("429 RESOURCE_EXHAUSTED: quota exceeded")
        return f"ok:{service.api_key}"

    monkeypatch.setattr(service, "_execute_api_call_once", fake_once)
    return service, calls


@pytest.mark.asyncio
async def test_rotates_to_next_key_on_quota_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, calls = _make_service(monkeypatch, ["k1", "k2", "k3"], failing={"k1"})
    result = await service._execute_api_call("hi", "sys", 0.2)
    assert result == "ok:k2"
    assert calls == ["k1", "k2"]
    assert service._key_index == 1


@pytest.mark.asyncio
async def test_raises_when_all_keys_exhausted(monkeypatch: pytest.MonkeyPatch) -> None:
    service, calls = _make_service(monkeypatch, ["k1", "k2"], failing={"k1", "k2"})
    with pytest.raises(RuntimeError):
        await service._execute_api_call("hi", "sys", 0.2)
    assert calls == ["k1", "k2"]


@pytest.mark.asyncio
async def test_blocked_key_is_skipped_on_next_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, calls = _make_service(monkeypatch, ["k1", "k2"], failing={"k1"})
    await service._execute_api_call("a", "sys", 0.2)
    await service._execute_api_call("b", "sys", 0.2)
    assert calls == ["k1", "k2", "k2"]


@pytest.mark.asyncio
async def test_non_retryable_error_does_not_rotate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, _ = _make_service(monkeypatch, ["k1", "k2"], failing=set())

    async def boom(*args: Any, **kwargs: Any) -> str:
        raise LLMServiceException("Empty response returned from LLM provider")

    monkeypatch.setattr(service, "_execute_api_call_once", boom)
    with pytest.raises(LLMServiceException):
        await service._execute_api_call("hi", "sys", 0.2)
    assert service._key_index == 0
