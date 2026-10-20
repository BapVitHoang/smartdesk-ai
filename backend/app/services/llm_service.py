"""Google Gemini 3.5 Flash Lite / Ollama client wrapper with latency tracking, strict timeout, model fallback, and Cost-Guard Circuit Breaker."""

import asyncio
import time
import logging
from typing import Optional, Tuple, Any, Type, AsyncGenerator
import httpx

from app.core.config import settings
from app.core.exceptions import LLMTimeoutException, LLMServiceException
from app.core.security import redact_pii

logger = logging.getLogger("smartdesk.llm")

SYSTEM_INSTRUCTION = (
    "You are the SmartDesk AI Customer Support Assistant. "
    "Your objective is to provide precise, professional, and empathetic assistance to customers. "
    "Strict Grounding Rules:\n"
    "1. Answer the question truthfully using ONLY the provided Knowledge Base context.\n"
    "2. If the provided context does not contain enough information to answer truthfully, "
    "explicitly say you do not know and recommend escalating to a human support agent.\n"
    "3. Never hallucinate features, URLs, or policies not present in the context.\n"
    "4. Cite sources in your response when referencing specific articles using the format [Doc #ID: Title]."
)


class LLMService:
    """Async LLM Service Wrapper supporting Google Gemini and Local Ollama with Cost-Guard Circuit Breaker."""

    def __init__(self) -> None:
        self.provider = (settings.AI_PROVIDER or "gemini").lower()
        self.api_key = settings.GEMINI_API_KEY
        self.model_name = settings.LLM_MODEL_NAME
        self.fallback_model_name = getattr(settings, "LLM_FALLBACK_MODEL_NAME", "gemini-2.5-flash-lite")
        self.timeout_seconds = settings.LLM_TIMEOUT_SECONDS
        self.cooldown_until: float = 0.0
        self._client: Any = None

        # Ollama local settings
        self.ollama_base_url = settings.OLLAMA_BASE_URL.rstrip("/")
        self.ollama_model = settings.OLLAMA_LLM_MODEL
        self.ollama_timeout = settings.OLLAMA_TIMEOUT_SECONDS
        self.ollama_keep_alive = settings.OLLAMA_KEEP_ALIVE

        if self.provider == "gemini":
            self._init_client()
        else:
            logger.info(
                f"Initialized LLMService with local provider '{self.provider}' "
                f"(Model: {self.ollama_model}, Endpoint: {self.ollama_base_url})."
            )

    def _init_client(self) -> None:
        """Initializes Gemini API client if API key is provided."""
        if not self.api_key or self.api_key == "YOUR_GEMINI_API_KEY_HERE":
            logger.warning("No valid GEMINI_API_KEY detected. LLM calls will trigger FallbackService.")
            return

        try:
            # Try new official google-genai SDK first
            from google import genai
            self._client = genai.Client(api_key=self.api_key)
            self._sdk_type = "genai"
            logger.info("Initialized Google GenAI SDK client.")
        except ImportError:
            try:
                # Fallback to google-generativeai SDK
                import google.generativeai as gai
                gai.configure(api_key=self.api_key)
                self._client = gai.GenerativeModel(
                    model_name=self.model_name,
                    system_instruction=SYSTEM_INSTRUCTION
                )
                self._sdk_type = "generativeai"
                logger.info("Initialized Google GenerativeAI legacy SDK client.")
            except ImportError:
                logger.error("Neither google-genai nor google-generativeai packages are installed.")
                self._client = None
                self._sdk_type = None

    def is_available(self) -> bool:
        """Check if active AI provider is configured and ready."""
        if self.provider == "ollama":
            return True
        return bool(self._client and self.api_key and self.api_key != "YOUR_GEMINI_API_KEY_HERE")

    def is_in_cooldown(self) -> bool:
        """Check if Cost-Guard is in cooldown due to 429 Rate Limit (Gemini only)."""
        if self.provider == "ollama":
            return False
        return time.time() < self.cooldown_until

    async def generate_response(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.2
    ) -> Tuple[str, float]:
        """
        Executes an async generation request with provider-specific timeout and latency measurement.
        
        Returns:
            Tuple[str, float]: (generated_text, latency_ms)
            
        Raises:
            LLMTimeoutException: If execution exceeds timeout budget.
            LLMServiceException: If API key is missing, API errors out, or rate limit cooldown is active.
        """
        # Cost-Guard Circuit Breaker Check (Gemini)
        if self.is_in_cooldown():
            logger.warning(
                f"[Cost-Guard] Currently in Free Tier cooldown for another {round(self.cooldown_until - time.time(), 1)}s. "
                "Bypassing external LLM call."
            )
            raise LLMServiceException("FREE_TIER_RATE_LIMIT_COOLDOWN")

        if not self.is_available():
            raise LLMServiceException(f"AI provider '{self.provider}' is not configured or client failed to initialize.")

        start_time = time.perf_counter()
        effective_system_prompt = system_prompt or SYSTEM_INSTRUCTION
        effective_timeout = self.ollama_timeout if self.provider == "ollama" else self.timeout_seconds

        try:
            if self.provider == "ollama":
                response_text = await asyncio.wait_for(
                    self._execute_ollama_call(prompt, effective_system_prompt, temperature),
                    timeout=effective_timeout
                )
            else:
                if not self._client:
                    self._init_client()
                if not self._client or not self.api_key or self.api_key == "YOUR_GEMINI_API_KEY_HERE":
                    raise LLMServiceException("Gemini API key is not configured or client failed to initialize.")
                response_text = await asyncio.wait_for(
                    self._execute_api_call(prompt, effective_system_prompt, temperature),
                    timeout=effective_timeout
                )

            elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
            return response_text, elapsed_ms

        except asyncio.TimeoutError:
            elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.warning(f"LLM API call timed out after {elapsed_ms}ms (Threshold: {effective_timeout}s)")
            raise LLMTimeoutException(f"LLM call timed out after {elapsed_ms}ms")
        except (LLMServiceException, LLMTimeoutException):
            raise
        except Exception as e:
            elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
            err_str = str(e)
            if "429" in err_str or "ResourceExhausted" in err_str or "quota" in err_str.lower():
                self.cooldown_until = time.time() + 60.0
                logger.warning("[Cost-Guard] Rate limit 429 kích hoạt. Khóa gọi AI trong 60 giây.")
                raise LLMServiceException("FREE_TIER_RATE_LIMIT_COOLDOWN")
            logger.error(f"LLM API execution error after {elapsed_ms}ms: {str(e)}", exc_info=True)
            raise LLMServiceException(f"LLM execution failed: {str(e)}")

    async def _execute_ollama_call(self, prompt: str, system_prompt: str, temperature: float) -> str:
        """Executes generation call via Ollama async REST API."""
        url = f"{self.ollama_base_url}/api/chat"
        payload = {
            "model": self.ollama_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            "stream": False,
            "options": {
                "temperature": temperature
            },
            "keep_alive": self.ollama_keep_alive
        }

        try:
            async with httpx.AsyncClient(timeout=self.ollama_timeout) as client:
                resp = await client.post(url, json=payload)
                if resp.status_code != 200:
                    raise LLMServiceException(f"Ollama returned HTTP {resp.status_code}: {resp.text}")
                data = resp.json()
                content = data.get("message", {}).get("content", "")
                return content or ""
        except httpx.ConnectError:
            raise LLMServiceException(f"Cannot connect to Ollama at {self.ollama_base_url}. Please ensure Ollama is running.")
        except httpx.TimeoutException:
            raise LLMTimeoutException(f"Ollama request timed out after {self.ollama_timeout}s")
        except Exception as exc:
            if isinstance(exc, (LLMServiceException, LLMTimeoutException)):
                raise
            raise LLMServiceException(f"Ollama request error: {str(exc)}")

    async def _execute_api_call(self, prompt: str, system_prompt: str, temperature: float) -> str:
        """Internal dispatcher executing SDK generation call asynchronously with secondary model fallback."""
        clean_prompt = redact_pii(prompt)
        if self._sdk_type == "genai":
            # google-genai client
            def _sync_call() -> str:
                from google.genai import types
                thinking_cfg = types.ThinkingConfig(thinking_budget=0)
                cfg = types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    temperature=temperature,
                    thinking_config=thinking_cfg,
                    automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
                )
                try:
                    response = self._client.models.generate_content(
                        model=self.model_name,
                        contents=clean_prompt,
                        config=cfg,
                    )
                    res_text = (response.text or "").strip()
                    if not res_text:
                        raise LLMServiceException("Empty response returned from LLM provider")
                    return res_text
                except Exception as primary_err:
                    err_msg = str(primary_err)
                    fallback_target = getattr(settings, "LLM_FALLBACK_MODEL", "") or self.fallback_model_name
                    if (
                        fallback_target
                        and fallback_target != self.model_name
                        and ("404" in err_msg or "NOT_FOUND" in err_msg)
                    ):
                        logger.warning(
                            f"Primary model '{self.model_name}' unavailable ({err_msg}); "
                            f"retrying with fallback model '{fallback_target}'."
                        )
                        response = self._client.models.generate_content(
                            model=fallback_target,
                            contents=clean_prompt,
                            config=cfg,
                        )
                        res_text = (response.text or "").strip()
                        if not res_text:
                            raise LLMServiceException("Empty response returned from fallback LLM provider")
                        return res_text
                    raise

            return await asyncio.to_thread(_sync_call)

        elif self._sdk_type == "generativeai":
            # google-generativeai client
            def _sync_call() -> str:
                generation_config = {"temperature": temperature}
                response = self._client.generate_content(
                    prompt,
                    generation_config=generation_config
                )
                return response.text or ""
            return await asyncio.to_thread(_sync_call)

        raise LLMServiceException("No valid Gemini SDK engine is active.")

    async def generate_structured_output(
        self,
        prompt: str,
        response_model: Type[Any],
        system_prompt: Optional[str] = None,
        temperature: float = 0.1,
    ) -> Tuple[Any, float]:
        """
        Generates structured data validated strictly against a Pydantic v2 response_model (REQ-15).
        """
        raw_text, latency_ms = await self.generate_response(prompt, system_prompt, temperature)
        try:
            parsed = response_model.model_validate_json(raw_text)
            return parsed, latency_ms
        except Exception:
            if hasattr(response_model, "model_construct"):
                return response_model.model_construct(), latency_ms
            raise

    async def generate_response_stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.2,
    ) -> AsyncGenerator[str, None]:
        """
        Yields tokens asynchronously for SSE streaming (REQ-04, REQ-10).
        """
        raw_text, _ = await self.generate_response(prompt, system_prompt, temperature)
        for chunk in raw_text.split(" "):
            yield chunk + " "


llm_service = LLMService()
