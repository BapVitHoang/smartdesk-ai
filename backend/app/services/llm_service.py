"""Google Gemini 3.5 Flash Lite / Ollama client wrapper with latency tracking, token/cost telemetry, structured output, SSE streaming, and Cost-Guard Circuit Breaker."""

import asyncio
import json
import logging
import os
import re
import time
from typing import Any, AsyncGenerator, Callable, Dict, List, Optional, Tuple, Type
import httpx

from app.core.config import settings
from app.core.exceptions import LLMServiceException, LLMTimeoutException
from app.core.prompts import prompt_registry
from app.core.security import redact_pii

logger = logging.getLogger("smartdesk.llm")


def scrub_sensitive(text: str, api_key: Optional[str] = None) -> str:
    """Removes API keys and sensitive credentials from error messages and logs."""
    if not text:
        return ""
    scrubbed = str(text)
    if api_key and len(api_key) > 6:
        scrubbed = scrubbed.replace(api_key, "[REDACTED_API_KEY]")
    # Mask common Google API key pattern AIzaSy...
    scrubbed = re.sub(r"AIzaSy[A-Za-z0-9_\-]{33}", "[REDACTED_API_KEY]", scrubbed)
    return scrubbed


class LLMConfigException(LLMServiceException):
    """Raised when an external API call fails with HTTP 400/401/403/404 client or configuration error."""

    def __init__(
        self, message: str, status_code: int = 400, details: Optional[Any] = None
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.details = details
        self.telemetry_status = "config_error"


def default_system_instruction() -> str:
    """Returns the versioned default system instruction from backend/data/prompts.json."""
    return prompt_registry.render("default_system_instruction")


PLACEHOLDER_API_KEY = "YOUR_GEMINI_API_KEY_HERE"
INVALID_KEY_COOLDOWN_SECONDS = 3600.0


def _is_quota_error(err_str: str) -> bool:
    return (
        "429" in err_str
        or "ResourceExhausted" in err_str
        or "RESOURCE_EXHAUSTED" in err_str
        or "quota" in err_str.lower()
    )


def _is_invalid_key_error(err_str: str) -> bool:
    return any(
        marker in err_str
        for marker in (
            "401",
            "403",
            "API_KEY_INVALID",
            "PERMISSION_DENIED",
            "UNAUTHENTICATED",
        )
    )


def load_gemini_api_keys() -> List[str]:
    """Reads GEMINI_API_KEYS (comma/newline list or JSON array) plus GEMINI_API_KEY, de-duplicated, order preserved."""
    # An env var (even empty) overrides .env, matching pydantic-settings precedence.
    raw = os.environ.get("GEMINI_API_KEYS")
    if raw is None:
        raw = ""
        try:
            from dotenv import dotenv_values

            for env_path in settings.model_config.get("env_file") or []:
                value = dotenv_values(env_path).get("GEMINI_API_KEYS")
                if value:
                    raw = value
        except ImportError:
            pass

    candidates: List[str] = []
    raw = (raw or "").strip()
    if raw.startswith("["):
        try:
            candidates = [str(k) for k in json.loads(raw)]
        except json.JSONDecodeError:
            candidates = []
    else:
        candidates = raw.replace("\n", ",").split(",")
    candidates.append(settings.GEMINI_API_KEY or "")

    keys: List[str] = []
    for key in candidates:
        key = key.strip().strip('"').strip("'")
        if key and key != PLACEHOLDER_API_KEY and key not in keys:
            keys.append(key)
    return keys


class LLMService:
    """Async LLM Service Wrapper supporting Google Gemini and Local Ollama with Cost-Guard Circuit Breaker."""

    def __init__(self) -> None:
        self.provider = (settings.AI_PROVIDER or "gemini").lower()
        self.api_keys: List[str] = load_gemini_api_keys()
        self._key_index: int = 0
        self._key_blocked_until: Dict[int, float] = {}
        self.api_key = self.api_keys[0] if self.api_keys else ""
        self.model_name = settings.LLM_MODEL_NAME
        self.fallback_model_name = getattr(
            settings, "LLM_FALLBACK_MODEL_NAME", "gemini-2.5-flash-lite"
        )
        self.timeout_seconds = settings.LLM_TIMEOUT_SECONDS
        self.cooldown_until: float = 0.0
        self._client: Any = None
        self._sdk_type: Optional[str] = None

        # Token & Cost Telemetry Tracking (REQ-22)
        self.last_input_tokens: int = 0
        self.last_output_tokens: int = 0
        self.last_cost_usd: float = 0.0

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
        if not self.api_key or self.api_key == PLACEHOLDER_API_KEY:
            logger.warning(
                "No valid GEMINI_API_KEY detected. LLM calls will trigger FallbackService."
            )
            return

        try:
            from google import genai

            self._client = genai.Client(api_key=self.api_key)
            self._sdk_type = "genai"
            logger.info("Initialized Google GenAI SDK client.")
        except ImportError:
            try:
                import google.generativeai as gai

                gai.configure(api_key=self.api_key)
                self._client = gai.GenerativeModel(
                    model_name=self.model_name,
                    system_instruction=default_system_instruction(),
                )
                self._sdk_type = "generativeai"
                logger.info("Initialized Google GenerativeAI legacy SDK client.")
            except ImportError:
                logger.error(
                    "Neither google-genai nor google-generativeai packages are installed."
                )
                self._client = None
                self._sdk_type = None

    def _activate_key(self, index: int) -> None:
        """Switches the active Gemini key and rebuilds the SDK client."""
        self._key_index = index
        self.api_key = self.api_keys[index]
        self._client = None
        self._init_client()

    def _next_available_key_index(self) -> Optional[int]:
        """Returns the first key index (starting at the active one) that is not blocked."""
        now = time.time()
        total = len(self.api_keys)
        for offset in range(total):
            idx = (self._key_index + offset) % total
            if self._key_blocked_until.get(idx, 0.0) <= now:
                return idx
        return None

    def _rotate_key(self, err_str: str) -> bool:
        """Blocks the failing key and activates the next usable one. Returns False when none is left."""
        if len(self.api_keys) <= 1 or self.api_key not in self.api_keys:
            return False
        block_secs = (
            INVALID_KEY_COOLDOWN_SECONDS
            if _is_invalid_key_error(err_str)
            else float(getattr(settings, "RATE_LIMIT_COOLDOWN_SECONDS", 60))
        )
        failed_index = self._key_index
        self._key_blocked_until[failed_index] = time.time() + block_secs
        next_index = self._next_available_key_index()
        if next_index is None:
            return False
        logger.warning(
            f"[Key-Rotation] Gemini key #{failed_index + 1}/{len(self.api_keys)} blocked for {int(block_secs)}s; "
            f"switching to key #{next_index + 1}."
        )
        self._activate_key(next_index)
        return True

    def is_available(self) -> bool:
        """Check if active AI provider is configured and ready."""
        if self.provider == "ollama":
            return True
        return bool(
            self._client and self.api_key and self.api_key != "YOUR_GEMINI_API_KEY_HERE"
        )

    def is_in_cooldown(self) -> bool:
        """Check if Cost-Guard is in cooldown due to 429 Rate Limit (Gemini only)."""
        if self.provider == "ollama":
            return False
        return time.time() < self.cooldown_until

    def reset_cooldown(self) -> None:
        """Resets the 60s Cost-Guard Circuit Breaker cooldown lock."""
        self.cooldown_until = 0.0
        self._key_blocked_until.clear()
        try:
            from app.services.embedding_service import embedding_service

            embedding_service.rate_limited_until = 0.0
        except Exception:
            pass
        logger.info(
            "[Cost-Guard] Cooldown state manually reset. Cloud LLM calls re-enabled."
        )

    @staticmethod
    def estimate_tokens(text: str) -> int:
        """Estimates token count (~4 chars per token) when provider omits usage metadata."""
        if not text:
            return 0
        return max(1, len(text) // 4)

    def calculate_cost_usd(self, input_tokens: int, output_tokens: int) -> float:
        """Calculates real USD cost based on configured per-1M token pricing (0.0 for local Ollama)."""
        if self.provider == "ollama":
            return 0.0
        in_rate = getattr(settings, "LLM_INPUT_COST_PER_MILLION", 0.30)
        out_rate = getattr(settings, "LLM_OUTPUT_COST_PER_MILLION", 2.50)
        cost = (input_tokens / 1_000_000.0) * in_rate + (
            output_tokens / 1_000_000.0
        ) * out_rate
        return round(cost, 6)

    def _record_token_metrics(
        self,
        prompt: str,
        system_prompt: str,
        response_text: str,
        in_tok: int = 0,
        out_tok: int = 0,
    ) -> None:
        """Updates last_input_tokens, last_output_tokens, and last_cost_usd."""
        self.last_input_tokens = (
            in_tok if in_tok > 0 else self.estimate_tokens(f"{system_prompt}\n{prompt}")
        )
        self.last_output_tokens = (
            out_tok if out_tok > 0 else self.estimate_tokens(response_text)
        )
        self.last_cost_usd = self.calculate_cost_usd(
            self.last_input_tokens, self.last_output_tokens
        )

    @property
    def active_model_name(self) -> str:
        """Returns the active model identifier for telemetry."""
        return self.ollama_model if self.provider == "ollama" else self.model_name

    def _sanitize_contents(self, contents: Any) -> Any:
        """
        Sanitizes request contents for Gemini 3.5 constraints:
        1. Role 'system' inside contents is rejected (must be in system_instruction).
        2. Trailing 'model' turns are rejected (request cannot end with a model turn).
        """
        if not isinstance(contents, list):
            return contents

        filtered = [
            turn
            for turn in contents
            if not (
                isinstance(turn, dict) and str(turn.get("role", "")).lower() == "system"
            )
        ]

        while (
            filtered
            and isinstance(filtered[-1], dict)
            and str(filtered[-1].get("role", "")).lower() == "model"
        ):
            filtered.pop()

        return filtered

    def _parse_and_classify_error(self, exc: Exception) -> Tuple[int, str]:
        """
        Extracts HTTP status code and clean error string from exception.
        Returns:
            Tuple[int, str]: (status_code, error_message)
        """
        err_str = str(exc)
        code = getattr(exc, "code", getattr(exc, "status_code", None))
        status_name = str(getattr(exc, "status", "")).upper()

        if code is not None:
            try:
                code_int = int(code)
                return code_int, err_str
            except (ValueError, TypeError):
                pass

        if (
            "400" in err_str
            or "INVALID_ARGUMENT" in err_str
            or "INVALID_ARGUMENT" in status_name
        ):
            return 400, err_str
        if (
            "401" in err_str
            or "UNAUTHENTICATED" in err_str
            or "UNAUTHENTICATED" in status_name
        ):
            return 401, err_str
        if (
            "403" in err_str
            or "PERMISSION_DENIED" in err_str
            or "PERMISSION_DENIED" in status_name
        ):
            return 403, err_str
        if "404" in err_str or "NOT_FOUND" in err_str or "NOT_FOUND" in status_name:
            return 404, err_str
        if (
            "429" in err_str
            or "RESOURCE_EXHAUSTED" in err_str
            or "quota" in err_str.lower()
        ):
            return 429, err_str
        if "503" in err_str or "UNAVAILABLE" in err_str:
            return 503, err_str
        if "504" in err_str or "DEADLINE_EXCEEDED" in err_str:
            return 504, err_str
        if "500" in err_str or "INTERNAL" in err_str:
            return 500, err_str

        return 500, err_str

    async def generate_response(
        self, prompt: str, system_prompt: Optional[str] = None, temperature: float = 0.2
    ) -> Tuple[str, float]:
        """
        Executes an async generation request with provider-specific timeout and latency measurement.

        Returns:
            Tuple[str, float]: (generated_text, latency_ms)
        """
        if self.is_in_cooldown():
            logger.warning(
                f"[Cost-Guard] Currently in Free Tier cooldown for another {round(self.cooldown_until - time.time(), 1)}s. "
                "Bypassing external LLM call."
            )
            raise LLMServiceException("FREE_TIER_RATE_LIMIT_COOLDOWN")

        if not self.is_available():
            raise LLMServiceException(
                f"AI provider '{self.provider}' is not configured or client failed to initialize."
            )

        start_time = time.perf_counter()
        effective_system_prompt = system_prompt or default_system_instruction()
        effective_timeout = (
            self.ollama_timeout if self.provider == "ollama" else self.timeout_seconds
        )

        max_retries = 1
        attempt = 0

        while attempt <= max_retries:
            try:
                if self.provider == "ollama":
                    response_text = await asyncio.wait_for(
                        self._execute_ollama_call(
                            prompt, effective_system_prompt, temperature
                        ),
                        timeout=effective_timeout,
                    )
                else:
                    if not self._client:
                        self._init_client()
                    if (
                        not self._client
                        or not self.api_key
                        or self.api_key == "YOUR_GEMINI_API_KEY_HERE"
                    ):
                        raise LLMServiceException(
                            "Gemini API key is not configured or client failed to initialize."
                        )
                    response_text = await asyncio.wait_for(
                        self._execute_api_call(
                            prompt, effective_system_prompt, temperature
                        ),
                        timeout=effective_timeout,
                    )

                elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
                return response_text, elapsed_ms

            except asyncio.TimeoutError:
                elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
                logger.warning(
                    f"LLM API call timed out after {elapsed_ms}ms (Threshold: {effective_timeout}s, attempt {attempt + 1})"
                )
                if attempt < max_retries:
                    attempt += 1
                    await asyncio.sleep(1.0)
                    continue
                raise LLMTimeoutException(f"LLM call timed out after {elapsed_ms}ms")

            except (LLMConfigException, LLMServiceException, LLMTimeoutException):
                raise

            except Exception as e:
                elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
                status_code, err_msg = self._parse_and_classify_error(e)
                clean_err_msg = scrub_sensitive(err_msg, self.api_key)

                # HTTP 400, 401, 403, 404: Client / Configuration errors
                # NEVER retry, NEVER set cooldown, log once at ERROR level
                if status_code in (400, 401, 403, 404):
                    logger.error(
                        f"[LLM Config Error] External API rejected request with HTTP {status_code} after {elapsed_ms}ms: {clean_err_msg}"
                    )
                    raise LLMConfigException(clean_err_msg, status_code=status_code)

                # HTTP 429 / Quota / Rate limit
                elif status_code == 429:
                    retry_after = getattr(e, "retry_after", None)
                    if retry_after is not None:
                        try:
                            retry_after = float(retry_after)
                        except (ValueError, TypeError):
                            retry_after = None

                    if (
                        attempt < max_retries
                        and retry_after is not None
                        and retry_after <= 5.0
                    ):
                        logger.info(
                            f"[Cost-Guard] Honoring Retry-After ({retry_after}s) before retrying..."
                        )
                        attempt += 1
                        await asyncio.sleep(retry_after)
                        continue

                    cooldown_secs = float(
                        getattr(settings, "RATE_LIMIT_COOLDOWN_SECONDS", 60)
                    )
                    self.cooldown_until = time.time() + cooldown_secs
                    logger.warning(
                        f"[Cost-Guard] Rate limit 429 kích hoạt. Khóa gọi AI trong {int(cooldown_secs)} giây: {clean_err_msg}"
                    )
                    raise LLMServiceException("FREE_TIER_RATE_LIMIT_COOLDOWN")

                # HTTP 5xx: Upstream server error -> limited retry (1 bounded retry), then fallback
                elif status_code in (500, 502, 503, 504):
                    if attempt < max_retries:
                        logger.warning(
                            f"[LLM Upstream Error] HTTP {status_code} on attempt {attempt + 1}: {clean_err_msg}. Retrying in 1.0s..."
                        )
                        attempt += 1
                        await asyncio.sleep(1.0)
                        continue
                    logger.error(
                        f"[LLM Upstream Error] HTTP {status_code} after {attempt + 1} attempts: {clean_err_msg}"
                    )
                    raise LLMServiceException(
                        f"LLM upstream error {status_code}: {clean_err_msg}"
                    )

                # Other unexpected exceptions
                logger.error(
                    f"LLM API execution error after {elapsed_ms}ms: {clean_err_msg}",
                    exc_info=True,
                )
                raise LLMServiceException(f"LLM execution failed: {clean_err_msg}")

    async def _execute_ollama_call(
        self,
        prompt: str,
        system_prompt: str,
        temperature: float,
        json_mode: bool = False,
    ) -> str:
        """Executes generation call via Ollama async REST API."""
        url = f"{self.ollama_base_url}/api/chat"
        payload: Dict[str, Any] = {
            "model": self.ollama_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            "stream": False,
            "options": {"temperature": temperature},
            "keep_alive": self.ollama_keep_alive,
        }
        if json_mode:
            payload["format"] = "json"

        try:
            async with httpx.AsyncClient(timeout=self.ollama_timeout) as client:
                resp = await client.post(url, json=payload)
                if resp.status_code != 200:
                    raise LLMServiceException(
                        f"Ollama returned HTTP {resp.status_code}: {resp.text}"
                    )
                data = resp.json()
                content = (data.get("message", {}).get("content", "") or "").strip()
                if not content:
                    raise LLMServiceException(
                        "Empty response returned from Ollama provider"
                    )
                in_tok = int(data.get("prompt_eval_count", 0) or 0)
                out_tok = int(data.get("eval_count", 0) or 0)
                self._record_token_metrics(
                    prompt, system_prompt, content, in_tok, out_tok
                )
                return content
        except httpx.ConnectError:
            raise LLMServiceException(
                f"Cannot connect to Ollama at {self.ollama_base_url}. Please ensure Ollama is running."
            )
        except httpx.TimeoutException:
            raise LLMTimeoutException(
                f"Ollama request timed out after {self.ollama_timeout}s"
            )
        except Exception as exc:
            if isinstance(exc, (LLMServiceException, LLMTimeoutException)):
                raise
            raise LLMServiceException(f"Ollama request error: {str(exc)}")

    async def _execute_api_call(
        self,
        prompt: str,
        system_prompt: str,
        temperature: float,
        response_schema: Optional[Type[Any]] = None,
    ) -> str:
        """Runs the SDK call, rotating to the next Gemini key on quota or invalid-key errors."""
        if self.api_key in self.api_keys:
            start_index = self._next_available_key_index()
            if start_index is not None and start_index != self._key_index:
                self._activate_key(start_index)

        attempts = max(1, len(self.api_keys))
        for attempt in range(attempts):
            try:
                return await self._execute_api_call_once(
                    prompt, system_prompt, temperature, response_schema
                )
            except LLMServiceException:
                raise
            except Exception as exc:
                err_str = str(exc)
                retryable = _is_quota_error(err_str) or _is_invalid_key_error(err_str)
                if attempt < attempts - 1 and retryable and self._rotate_key(err_str):
                    continue
                raise
        raise LLMServiceException("All Gemini API keys failed.")

    async def _execute_api_call_once(
        self,
        prompt: str,
        system_prompt: str,
        temperature: float,
        response_schema: Optional[Type[Any]] = None,
    ) -> str:
        """Internal dispatcher executing SDK generation call asynchronously with secondary model fallback."""
        clean_prompt = redact_pii(prompt)
        if self._sdk_type == "genai":

            def _sync_call() -> Tuple[str, int, int]:
                from google.genai import types

                thinking_level_val = (
                    getattr(settings, "GEMINI_THINKING_LEVEL", "MINIMAL") or "MINIMAL"
                )
                thinking_cfg = types.ThinkingConfig(thinking_level=thinking_level_val)
                cfg_kwargs: Dict[str, Any] = {
                    "system_instruction": system_prompt,
                    "temperature": temperature,
                    "thinking_config": thinking_cfg,
                    "automatic_function_calling": types.AutomaticFunctionCallingConfig(
                        disable=True
                    ),
                }
                if response_schema is not None:
                    cfg_kwargs["response_mime_type"] = "application/json"
                    cfg_kwargs["response_schema"] = response_schema

                cfg = types.GenerateContentConfig(**cfg_kwargs)
                sanitized_contents = self._sanitize_contents(clean_prompt)
                try:
                    response = self._client.models.generate_content(
                        model=self.model_name,
                        contents=sanitized_contents,
                        config=cfg,
                    )
                except Exception as primary_err:
                    err_msg = str(primary_err)
                    fallback_target = (
                        getattr(settings, "LLM_FALLBACK_MODEL", "")
                        or self.fallback_model_name
                    )
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
                            contents=sanitized_contents,
                            config=cfg,
                        )
                    else:
                        raise

                res_text = (response.text or "").strip()
                if not res_text:
                    raise LLMServiceException(
                        "Empty response returned from LLM provider"
                    )

                usage = getattr(response, "usage_metadata", None)
                in_tok = (
                    int(getattr(usage, "prompt_token_count", 0) or 0) if usage else 0
                )
                out_tok = (
                    int(getattr(usage, "candidates_token_count", 0) or 0)
                    if usage
                    else 0
                )
                return res_text, in_tok, out_tok

            res_text, in_tok, out_tok = await asyncio.to_thread(_sync_call)
            self._record_token_metrics(
                clean_prompt, system_prompt, res_text, in_tok, out_tok
            )
            return res_text

        elif self._sdk_type == "generativeai":

            def _sync_call() -> str:
                generation_config = {"temperature": temperature}
                sanitized_contents = self._sanitize_contents(clean_prompt)
                response = self._client.generate_content(
                    sanitized_contents, generation_config=generation_config
                )
                return (response.text or "").strip()

            res_text = await asyncio.to_thread(_sync_call)
            if not res_text:
                raise LLMServiceException(
                    "Empty response returned from legacy Gemini SDK"
                )
            self._record_token_metrics(clean_prompt, system_prompt, res_text)
            return res_text

        raise LLMServiceException("No valid Gemini SDK engine is active.")

    @staticmethod
    def _extract_json_payload(raw_text: str) -> str:
        """Extracts JSON object or array string from raw LLM output (strips markdown fences if present)."""
        text = (raw_text or "").strip()
        fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text, re.IGNORECASE)
        if fence_match:
            return fence_match.group(1).strip()
        obj_match = re.search(r"(\{[\s\S]*\}|\[[\s\S]*\])", text)
        if obj_match:
            return obj_match.group(1).strip()
        return text

    async def generate_structured_output(
        self,
        prompt: str,
        response_model: Type[Any],
        system_prompt: Optional[str] = None,
        temperature: float = 0.1,
    ) -> Tuple[Any, float]:
        """
        Generates structured data validated strictly against a Pydantic v2 response_model (Capability C - REQ-15).

        Returns:
            Tuple[validated_instance, latency_ms]
        """
        schema_json = json.dumps(response_model.model_json_schema(), ensure_ascii=False)
        structured_instruction = (
            f"{system_prompt or default_system_instruction()}\n\n"
            f"IMPORTANT: Respond ONLY with valid JSON conforming to this schema:\n{schema_json}"
        )

        start_time = time.perf_counter()
        if self.is_in_cooldown():
            raise LLMServiceException("FREE_TIER_RATE_LIMIT_COOLDOWN")
        if not self.is_available():
            raise LLMServiceException(
                f"AI provider '{self.provider}' is not configured."
            )

        effective_timeout = (
            self.ollama_timeout if self.provider == "ollama" else self.timeout_seconds
        )
        max_retries = 1
        attempt = 0

        raw_text = ""
        while attempt <= max_retries:
            try:
                if self.provider == "ollama":
                    raw_text = await asyncio.wait_for(
                        self._execute_ollama_call(
                            prompt, structured_instruction, temperature, json_mode=True
                        ),
                        timeout=effective_timeout,
                    )
                else:
                    if not self._client:
                        self._init_client()
                    if not self._client:
                        raise LLMServiceException("Gemini client not initialized.")
                    raw_text = await asyncio.wait_for(
                        self._execute_api_call(
                            prompt,
                            structured_instruction,
                            temperature,
                            response_schema=response_model,
                        ),
                        timeout=effective_timeout,
                    )
                break

            except asyncio.TimeoutError:
                elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
                if attempt < max_retries:
                    attempt += 1
                    await asyncio.sleep(1.0)
                    continue
                raise LLMTimeoutException(
                    f"Structured LLM call timed out after {elapsed_ms}ms"
                )

            except (LLMConfigException, LLMServiceException, LLMTimeoutException):
                raise

            except Exception as exc:
                elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
                status_code, err_msg = self._parse_and_classify_error(exc)
                clean_err_msg = scrub_sensitive(err_msg, self.api_key)

                if status_code in (400, 401, 403, 404):
                    logger.error(
                        f"[LLM Config Error] Structured call rejected with HTTP {status_code} after {elapsed_ms}ms: {clean_err_msg}"
                    )
                    raise LLMConfigException(clean_err_msg, status_code=status_code)
                elif status_code == 429:
                    retry_after = getattr(exc, "retry_after", None)
                    if retry_after is not None:
                        try:
                            retry_after = float(retry_after)
                        except (ValueError, TypeError):
                            retry_after = None
                    if (
                        attempt < max_retries
                        and retry_after is not None
                        and retry_after <= 5.0
                    ):
                        attempt += 1
                        await asyncio.sleep(retry_after)
                        continue
                    cooldown_secs = float(
                        getattr(settings, "RATE_LIMIT_COOLDOWN_SECONDS", 60)
                    )
                    self.cooldown_until = time.time() + cooldown_secs
                    raise LLMServiceException("FREE_TIER_RATE_LIMIT_COOLDOWN")
                elif status_code in (500, 502, 503, 504):
                    if attempt < max_retries:
                        attempt += 1
                        await asyncio.sleep(1.0)
                        continue
                    raise LLMServiceException(
                        f"Structured output upstream error {status_code}: {clean_err_msg}"
                    )
                raise LLMServiceException(
                    f"Structured output call failed: {clean_err_msg}"
                )

        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
        cleaned_json = self._extract_json_payload(raw_text)

        try:
            validated = response_model.model_validate_json(cleaned_json)
            return validated, elapsed_ms
        except Exception as val_err:
            try:
                parsed_obj = json.loads(cleaned_json)
                if (
                    isinstance(parsed_obj, list)
                    and hasattr(response_model, "model_fields")
                    and "items" in response_model.model_fields
                ):
                    validated = response_model.model_validate({"items": parsed_obj})
                    return validated, elapsed_ms
                validated = response_model.model_validate(parsed_obj)
                return validated, elapsed_ms
            except Exception:
                logger.warning(
                    f"Structured output validation failed ({val_err}); raw: {cleaned_json[:160]}"
                )
                raise LLMServiceException(
                    f"Structured output schema validation failed: {val_err}"
                )

    def _classified_failure(
        self, exc: Exception, elapsed_ms: float, operation: str
    ) -> LLMServiceException:
        """Maps a provider exception to the Cost-Guard taxonomy (4xx config error, 429 cooldown, other failures)."""
        status_code, err_msg = self._parse_and_classify_error(exc)
        clean_err_msg = scrub_sensitive(err_msg, self.api_key)
        if status_code in (400, 401, 403, 404):
            logger.error(
                f"[LLM Config Error] {operation} rejected with HTTP {status_code} after {elapsed_ms}ms: {clean_err_msg}"
            )
            return LLMConfigException(clean_err_msg, status_code=status_code)
        if status_code == 429:
            cooldown_secs = float(getattr(settings, "RATE_LIMIT_COOLDOWN_SECONDS", 60))
            self.cooldown_until = time.time() + cooldown_secs
            logger.warning(
                f"[Cost-Guard] Rate limit 429 during {operation}. Khóa gọi AI trong {int(cooldown_secs)} giây."
            )
            return LLMServiceException("FREE_TIER_RATE_LIMIT_COOLDOWN")
        logger.error(f"{operation} failed after {elapsed_ms}ms: {clean_err_msg}")
        return LLMServiceException(f"{operation} failed: {clean_err_msg}")

    def _ensure_ready(self) -> None:
        """Raises LLMServiceException when the provider is in cooldown or not configured."""
        if self.is_in_cooldown():
            raise LLMServiceException("FREE_TIER_RATE_LIMIT_COOLDOWN")
        if not self.is_available():
            raise LLMServiceException(
                f"AI provider '{self.provider}' is not configured or client failed to initialize."
            )

    async def select_tool(
        self,
        message: str,
        tools: List[Dict[str, Any]],
        system_prompt: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Lets the LLM choose at most one tool through native function calling (Capability B - REQ-14).

        Returns:
            {"name": str, "args": dict} when the model emits a function call, otherwise None.
        """
        self._ensure_ready()
        start_time = time.perf_counter()
        effective_timeout = (
            self.ollama_timeout if self.provider == "ollama" else self.timeout_seconds
        )
        try:
            if self.provider == "ollama":
                call = self._select_tool_ollama(message, tools, system_prompt)
            else:
                call = self._select_tool_gemini(message, tools, system_prompt)
            return await asyncio.wait_for(call, timeout=effective_timeout)
        except asyncio.TimeoutError:
            elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
            raise LLMTimeoutException(f"Tool selection timed out after {elapsed_ms}ms")
        except (LLMServiceException, LLMTimeoutException):
            raise
        except Exception as exc:
            elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
            raise self._classified_failure(exc, elapsed_ms, "Tool selection")

    async def _select_tool_gemini(
        self, message: str, tools: List[Dict[str, Any]], system_prompt: str
    ) -> Optional[Dict[str, Any]]:
        if self._sdk_type != "genai":
            raise LLMServiceException(
                "Native function calling requires the google-genai SDK."
            )
        clean_message = redact_pii(message)

        def _sync_call() -> Tuple[Optional[Dict[str, Any]], int, int]:
            from google.genai import types

            declarations = [
                types.FunctionDeclaration(
                    name=t["name"],
                    description=t["description"],
                    parameters_json_schema=t["parameters"],
                )
                for t in tools
            ]
            cfg = types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=0.0,
                tools=[types.Tool(function_declarations=declarations)],
                tool_config=types.ToolConfig(
                    function_calling_config=types.FunctionCallingConfig(mode="AUTO")
                ),
                automatic_function_calling=types.AutomaticFunctionCallingConfig(
                    disable=True
                ),
                thinking_config=types.ThinkingConfig(
                    thinking_level=getattr(settings, "GEMINI_THINKING_LEVEL", "MINIMAL")
                    or "MINIMAL"
                ),
            )
            response = self._client.models.generate_content(
                model=self.model_name, contents=clean_message, config=cfg
            )
            usage = getattr(response, "usage_metadata", None)
            in_tok = int(getattr(usage, "prompt_token_count", 0) or 0) if usage else 0
            out_tok = (
                int(getattr(usage, "candidates_token_count", 0) or 0) if usage else 0
            )
            calls = getattr(response, "function_calls", None) or []
            if not calls:
                return None, in_tok, out_tok
            first = calls[0]
            return {"name": first.name, "args": dict(first.args or {})}, in_tok, out_tok

        selected, in_tok, out_tok = await asyncio.to_thread(_sync_call)
        self._record_token_metrics(
            clean_message, system_prompt, json.dumps(selected or {}), in_tok, out_tok
        )
        return selected

    async def _select_tool_ollama(
        self, message: str, tools: List[Dict[str, Any]], system_prompt: str
    ) -> Optional[Dict[str, Any]]:
        payload: Dict[str, Any] = {
            "model": self.ollama_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message},
            ],
            "tools": [
                {
                    "type": "function",
                    "function": {
                        "name": t["name"],
                        "description": t["description"],
                        "parameters": t["parameters"],
                    },
                }
                for t in tools
            ],
            "stream": False,
            "options": {"temperature": 0.0},
            "keep_alive": self.ollama_keep_alive,
        }
        try:
            async with httpx.AsyncClient(timeout=self.ollama_timeout) as client:
                resp = await client.post(
                    f"{self.ollama_base_url}/api/chat", json=payload
                )
        except httpx.ConnectError:
            raise LLMServiceException(
                f"Cannot connect to Ollama at {self.ollama_base_url}."
            )
        if resp.status_code != 200:
            raise LLMServiceException(
                f"Ollama returned HTTP {resp.status_code}: {resp.text}"
            )
        data = resp.json()
        tool_calls = (data.get("message") or {}).get("tool_calls") or []
        self._record_token_metrics(
            message,
            system_prompt,
            json.dumps(tool_calls),
            int(data.get("prompt_eval_count", 0) or 0),
            int(data.get("eval_count", 0) or 0),
        )
        if not tool_calls:
            return None
        fn = tool_calls[0].get("function") or {}
        args = fn.get("arguments") or {}
        if isinstance(args, str):
            args = json.loads(args or "{}")
        return {"name": fn.get("name", ""), "args": dict(args)}

    async def stream_generate(
        self,
        prompt: str,
        system_prompt: Optional[str],
        temperature: float,
        on_token: Callable[[str], None],
    ) -> Tuple[str, float]:
        """
        Streams the answer from the provider token-by-token (REQ-04, REQ-10), invoking on_token for each chunk.

        Returns:
            Tuple[str, float]: (full_text, latency_ms) once the stream completes.
        """
        self._ensure_ready()
        start_time = time.perf_counter()
        effective_system_prompt = system_prompt or default_system_instruction()
        effective_timeout = (
            self.ollama_timeout if self.provider == "ollama" else self.timeout_seconds
        )
        if self.provider != "ollama" and self._sdk_type != "genai":
            text, latency = await self.generate_response(
                prompt, effective_system_prompt, temperature
            )
            on_token(text)
            return text, latency

        stop_flag = {"stop": False}
        try:
            if self.provider == "ollama":
                stream_call = self._stream_ollama(
                    prompt, effective_system_prompt, temperature, on_token, stop_flag
                )
            else:
                stream_call = self._stream_gemini(
                    prompt, effective_system_prompt, temperature, on_token, stop_flag
                )
            text = await asyncio.wait_for(stream_call, timeout=effective_timeout)
        except asyncio.TimeoutError:
            stop_flag["stop"] = True
            elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
            raise LLMTimeoutException(f"LLM stream timed out after {elapsed_ms}ms")
        except (LLMServiceException, LLMTimeoutException):
            stop_flag["stop"] = True
            raise
        except Exception as exc:
            stop_flag["stop"] = True
            elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
            raise self._classified_failure(exc, elapsed_ms, "LLM stream")

        if not text.strip():
            raise LLMServiceException("Empty response returned from LLM provider")
        return text, round((time.perf_counter() - start_time) * 1000, 2)

    async def _stream_gemini(
        self,
        prompt: str,
        system_prompt: str,
        temperature: float,
        on_token: Callable[[str], None],
        stop_flag: Dict[str, bool],
    ) -> str:
        clean_prompt = redact_pii(prompt)
        loop = asyncio.get_running_loop()

        def _sync_stream() -> Tuple[str, int, int]:
            from google.genai import types

            cfg = types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=temperature,
                thinking_config=types.ThinkingConfig(
                    thinking_level=getattr(settings, "GEMINI_THINKING_LEVEL", "MINIMAL")
                    or "MINIMAL"
                ),
                automatic_function_calling=types.AutomaticFunctionCallingConfig(
                    disable=True
                ),
            )
            parts: List[str] = []
            in_tok = out_tok = 0
            for chunk in self._client.models.generate_content_stream(
                model=self.model_name,
                contents=self._sanitize_contents(clean_prompt),
                config=cfg,
            ):
                if stop_flag["stop"]:
                    break
                usage = getattr(chunk, "usage_metadata", None)
                if usage:
                    in_tok = int(getattr(usage, "prompt_token_count", 0) or in_tok)
                    out_tok = int(
                        getattr(usage, "candidates_token_count", 0) or out_tok
                    )
                piece = chunk.text or ""
                if piece:
                    parts.append(piece)
                    loop.call_soon_threadsafe(on_token, piece)
            return "".join(parts), in_tok, out_tok

        text, in_tok, out_tok = await asyncio.to_thread(_sync_stream)
        self._record_token_metrics(clean_prompt, system_prompt, text, in_tok, out_tok)
        return text

    async def _stream_ollama(
        self,
        prompt: str,
        system_prompt: str,
        temperature: float,
        on_token: Callable[[str], None],
        stop_flag: Dict[str, bool],
    ) -> str:
        payload: Dict[str, Any] = {
            "model": self.ollama_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            "stream": True,
            "options": {"temperature": temperature},
            "keep_alive": self.ollama_keep_alive,
        }
        parts: List[str] = []
        in_tok = out_tok = 0
        try:
            async with httpx.AsyncClient(timeout=self.ollama_timeout) as client:
                async with client.stream(
                    "POST", f"{self.ollama_base_url}/api/chat", json=payload
                ) as resp:
                    if resp.status_code != 200:
                        raise LLMServiceException(
                            f"Ollama returned HTTP {resp.status_code}"
                        )
                    async for line in resp.aiter_lines():
                        if stop_flag["stop"]:
                            break
                        if not line.strip():
                            continue
                        data = json.loads(line)
                        piece = (data.get("message") or {}).get("content", "")
                        if piece:
                            parts.append(piece)
                            on_token(piece)
                        if data.get("done"):
                            in_tok = int(data.get("prompt_eval_count", 0) or 0)
                            out_tok = int(data.get("eval_count", 0) or 0)
        except httpx.ConnectError:
            raise LLMServiceException(
                f"Cannot connect to Ollama at {self.ollama_base_url}. Please ensure Ollama is running."
            )
        text = "".join(parts)
        self._record_token_metrics(prompt, system_prompt, text, in_tok, out_tok)
        return text

    async def generate_response_stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.2,
    ) -> AsyncGenerator[str, None]:
        """Yields provider tokens as they arrive (REQ-04, REQ-10)."""
        queue: asyncio.Queue = asyncio.Queue()
        task = asyncio.create_task(
            self.stream_generate(prompt, system_prompt, temperature, queue.put_nowait)
        )
        while not (task.done() and queue.empty()):
            getter = asyncio.create_task(queue.get())
            done, _ = await asyncio.wait(
                {getter, task}, return_when=asyncio.FIRST_COMPLETED
            )
            if getter in done:
                yield getter.result()
            else:
                getter.cancel()
        task.result()


llm_service = LLMService()
