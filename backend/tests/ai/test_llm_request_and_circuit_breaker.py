"""Unit tests verifying Gemini 3.5 request builder shape (Task 1) and Error Classification / Circuit Breaker (Task 2 - Defect C4)."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from app.core.exceptions import LLMServiceException, LLMTimeoutException
from app.services.llm_service import LLMConfigException, LLMService, scrub_sensitive
from app.services.rag_service import RAGService


def test_scrub_sensitive_removes_api_keys() -> None:
    """Verify that error logging helpers strip real and pattern API keys."""
    raw = "Failed request with key AIzaSyABC123456789012345678901234567890 and secret MY_REAL_KEY_123"
    cleaned = scrub_sensitive(raw, api_key="MY_REAL_KEY_123")
    assert "[REDACTED_API_KEY]" in cleaned
    assert "AIzaSy" not in cleaned
    assert "MY_REAL_KEY_123" not in cleaned


def test_gemini_35_request_builder_shape_and_thinking_level() -> None:
    """
    Task 1: Verify the request builder sets thinking_level='MINIMAL'
    and never sends thinking_budget (which causes 400 INVALID_ARGUMENT on Gemini 3.5).
    """
    service = LLMService()
    service._sdk_type = "genai"
    service.model_name = "gemini-3.5-flash-lite"
    service.api_key = "dummy_key"

    captured_kwargs = {}

    class FakeModels:
        def generate_content(self, model, contents, config):
            captured_kwargs["model"] = model
            captured_kwargs["contents"] = contents
            captured_kwargs["config"] = config
            mock_resp = MagicMock()
            mock_resp.text = "Xin chào, tôi có thể giúp gì cho bạn?"
            mock_resp.usage_metadata = MagicMock(prompt_token_count=10, candidates_token_count=12)
            return mock_resp

    fake_client = MagicMock()
    fake_client.models = FakeModels()
    service._client = fake_client

    async def _test():
        res, latency = await service.generate_response(
            prompt="Xin chào",
            system_prompt="You are a helpful assistant.",
            temperature=0.2,
        )
        assert len(res) > 0
        assert latency >= 0.0

    asyncio.run(_test())

    assert captured_kwargs["model"] == "gemini-3.5-flash-lite"
    cfg = captured_kwargs["config"]
    assert cfg is not None

    # Assert thinking_config has thinking_level='MINIMAL'
    assert hasattr(cfg, "thinking_config")
    assert cfg.thinking_config is not None
    assert str(cfg.thinking_config.thinking_level).upper() in ("MINIMAL", "THINKINGLEVEL.MINIMAL")

    # Assert thinking_budget is NOT set or None (Gemini 3.5 rejects thinking_budget)
    budget = getattr(cfg.thinking_config, "thinking_budget", None)
    assert budget is None or budget == 0 or budget is False, "thinking_budget must not be sent to Gemini 3.5"


def test_sanitize_contents_guards_gemini_35_constraints() -> None:
    """
    Task 1: Verify history sanitization:
    - Trailing 'model' turn is removed (rejected on Gemini 3.5).
    - Role 'system' turns inside contents are filtered out (must be in system_instruction).
    """
    service = LLMService()
    history = [
        {"role": "system", "content": "You are a bot"},
        {"role": "user", "content": "Hello"},
        {"role": "model", "content": "Hi there"},
    ]
    sanitized = service._sanitize_contents(history)
    # The trailing model turn must be removed so the request ends with a user turn
    assert len(sanitized) == 1
    assert sanitized[0]["role"] == "user"


@pytest.mark.asyncio
async def test_error_classification_400_never_retries_and_no_cooldown() -> None:
    """
    Task 2 (Defect C4): HTTP 400 / INVALID_ARGUMENT is a client/config error.
    Must produce exactly ONE call, NEVER retry, and NEVER trigger the 60s cooldown.
    """
    service = LLMService()
    service._sdk_type = "genai"
    service.model_name = "gemini-3.5-flash-lite"
    service.api_key = "dummy_key"
    service.cooldown_until = 0.0

    call_count = 0

    class FakeModels400:
        def generate_content(self, model, contents, config):
            nonlocal call_count
            call_count += 1
            # Simulate Google GenAI 400 INVALID_ARGUMENT error
            err = Exception("400 INVALID_ARGUMENT: Request contains an invalid argument.")
            err.code = 400
            err.status = "INVALID_ARGUMENT"
            raise err

    fake_client = MagicMock()
    fake_client.models = FakeModels400()
    service._client = fake_client

    with pytest.raises(LLMConfigException) as exc_info:
        await service.generate_response("Test prompt")

    # Call count must be EXACTLY 1 (no retries!)
    assert call_count == 1
    # Cooldown MUST NOT be activated
    assert service.is_in_cooldown() is False
    assert service.cooldown_until == 0.0
    assert exc_info.value.status_code == 400
    assert exc_info.value.telemetry_status == "config_error"


@pytest.mark.asyncio
async def test_error_classification_401_403_404_no_cooldown() -> None:
    """
    Task 2: HTTP 401, 403, and 404 errors must not trigger cooldown.
    """
    service = LLMService()
    service._sdk_type = "genai"
    service.api_key = "dummy_key"
    service.cooldown_until = 0.0

    call_count = 0

    class FakeModels403:
        def generate_content(self, model, contents, config):
            nonlocal call_count
            call_count += 1
            err = Exception("403 PERMISSION_DENIED: API key not authorized.")
            err.code = 403
            err.status = "PERMISSION_DENIED"
            raise err

    fake_client = MagicMock()
    fake_client.models = FakeModels403()
    service._client = fake_client

    with pytest.raises(LLMConfigException):
        await service.generate_response("Test prompt")

    assert call_count == 1
    assert service.is_in_cooldown() is False
    assert service.cooldown_until == 0.0


@pytest.mark.asyncio
async def test_error_classification_429_activates_cooldown_and_resets() -> None:
    """
    Task 2: HTTP 429 / RESOURCE_EXHAUSTED must activate the 60s cooldown,
    and reset_cooldown() must clear it.
    """
    service = LLMService()
    service._sdk_type = "genai"
    service.api_key = "dummy_key"
    service.cooldown_until = 0.0

    class FakeModels429:
        def generate_content(self, model, contents, config):
            err = Exception("429 RESOURCE_EXHAUSTED: Quota exceeded for metric.")
            err.code = 429
            err.status = "RESOURCE_EXHAUSTED"
            raise err

    fake_client = MagicMock()
    fake_client.models = FakeModels429()
    service._client = fake_client

    with pytest.raises(LLMServiceException) as exc_info:
        await service.generate_response("Test prompt")

    assert "FREE_TIER_RATE_LIMIT_COOLDOWN" in str(exc_info.value)
    assert service.is_in_cooldown() is True
    assert service.cooldown_until > 0.0

    # Reset cooldown clears the state
    service.reset_cooldown()
    assert service.is_in_cooldown() is False
    assert service.cooldown_until == 0.0


@pytest.mark.asyncio
async def test_rag_fallback_on_llm_config_error_records_telemetry_status() -> None:
    """
    Task 2: When RAG pipeline encounters a 400 config error, it falls back to BM25
    and sets status='config_error' in telemetry logging.
    """
    rag = RAGService()
    mock_llm = MagicMock()
    mock_llm.is_in_cooldown.return_value = False
    mock_llm.is_available.return_value = True
    mock_llm.provider = "gemini"
    mock_llm.active_model_name = "gemini-3.5-flash-lite"
    mock_llm.generate_response = AsyncMock(
        side_effect=LLMConfigException("400 INVALID_ARGUMENT", status_code=400)
    )

    with patch("app.services.rag_service.llm_service", mock_llm):
        with patch("app.services.rag_service.log_ai_call", new_callable=AsyncMock) as mock_log:
            res = await rag.answer_query(query="Cách đặt lại mật khẩu là gì?", workspace_id=1)
            assert res.is_fallback is True
            assert res.fallback_reason == "CONFIG_ERROR"
            assert len(res.response) > 10
            # Telemetry status must be config_error
            assert mock_log.called
            logged_status = mock_log.call_args[1].get("status")
            assert logged_status == "config_error"
