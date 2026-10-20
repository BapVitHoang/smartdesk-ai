"""Unit tests for Local Ollama AI Provider integration in SmartDesk AI."""

import pytest
import httpx
from unittest.mock import AsyncMock, patch

from app.core.config import settings
from app.core.exceptions import LLMServiceException, LLMTimeoutException
from app.services.llm_service import LLMService
from app.services.embedding_service import EmbeddingService


@pytest.fixture
def ollama_llm():
    """Create an LLMService instance configured for Ollama."""
    with patch.object(settings, "AI_PROVIDER", "ollama"):
        service = LLMService()
        return service


@pytest.fixture
def ollama_embedding():
    """Create an EmbeddingService instance configured for Ollama."""
    with patch.object(settings, "AI_PROVIDER", "ollama"):
        service = EmbeddingService()
        return service


def test_ollama_llm_availability_and_cooldown(ollama_llm):
    """Ollama provider is always available and never in 429 cooldown."""
    assert ollama_llm.is_available() is True
    assert ollama_llm.is_in_cooldown() is False


def test_ollama_embedding_rate_limit(ollama_embedding):
    """Ollama embedding is never rate limited by Free Tier quotas."""
    assert ollama_embedding.is_rate_limited() is False


@pytest.mark.asyncio
async def test_ollama_llm_generate_success(ollama_llm):
    """Test successful response generation via Ollama /api/chat."""
    mock_resp = httpx.Response(
        200,
        json={"message": {"role": "assistant", "content": "Xin chào! Đây là câu trả lời từ Qwen 2.5."}},
        request=httpx.Request("POST", "http://localhost:11434/api/chat")
    )

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_resp
        text, latency = await ollama_llm.generate_response("Xin chào")

        assert "Qwen 2.5" in text
        assert latency >= 0.0
        assert mock_post.called
        call_args = mock_post.call_args
        assert "/api/chat" in call_args[0][0]
        payload = call_args[1]["json"]
        assert payload["model"] == ollama_llm.ollama_model
        assert payload["messages"][1]["content"] == "Xin chào"


@pytest.mark.asyncio
async def test_ollama_llm_connection_error(ollama_llm):
    """Test that connection error (Ollama not running) raises LLMServiceException."""
    with patch("httpx.AsyncClient.post", side_effect=httpx.ConnectError("Connection refused")):
        with pytest.raises(LLMServiceException) as exc_info:
            await ollama_llm.generate_response("Xin chào")
        assert "Cannot connect to Ollama" in str(exc_info.value)


@pytest.mark.asyncio
async def test_ollama_llm_timeout_error(ollama_llm):
    """Test that timeout error raises LLMTimeoutException."""
    with patch("httpx.AsyncClient.post", side_effect=httpx.TimeoutException("Read timed out")):
        with pytest.raises(LLMTimeoutException):
            await ollama_llm.generate_response("Xin chào")


@pytest.mark.asyncio
async def test_ollama_embedding_success(ollama_embedding):
    """Test successful embedding generation via Ollama /api/embed."""
    dummy_vec = [0.05] * 768
    mock_resp = httpx.Response(
        200,
        json={"embeddings": [dummy_vec]},
        request=httpx.Request("POST", "http://localhost:11434/api/embed")
    )

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_resp
        vec = await ollama_embedding.get_text_embedding("Đoạn văn kiểm thử")

        assert len(vec) == 768
        assert vec == dummy_vec


@pytest.mark.asyncio
async def test_ollama_embedding_fallback_on_error(ollama_embedding):
    """Test that failure in Ollama embedding gracefully falls back to pseudo-embeddings."""
    with patch("httpx.AsyncClient.post", side_effect=httpx.ConnectError("Ollama down")):
        vec = await ollama_embedding.get_text_embedding("Đoạn văn kiểm thử")

        assert len(vec) == 768
        # Should be a normalized non-empty vector
        assert sum(x * x for x in vec) > 0.0
