"""Google Gemini 3.5 Flash Lite / Ollama client wrapper with latency tracking, token/cost telemetry, structured output, SSE streaming, and Cost-Guard Circuit Breaker."""

import asyncio
import json
import logging
import os
import re
import time
from typing import Any, AsyncGenerator, Dict, List, Optional, Tuple, Type
import httpx

from app.core.config import settings
from app.core.exceptions import LLMServiceException, LLMTimeoutException
from app.core.prompts import prompt_registry
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
    raw = os.environ.get("GEMINI_API_KEYS", "")
    if not raw:
        try:
            from dotenv import dotenv_values

            # Same env files as Settings; later files win, matching pydantic-settings precedence.
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
                    model_name=self.model_name, system_instruction=SYSTEM_INSTRUCTION
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
        if len(self.api_keys) <= 1:
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
        effective_system_prompt = system_prompt or SYSTEM_INSTRUCTION
        effective_timeout = (
            self.ollama_timeout if self.provider == "ollama" else self.timeout_seconds
        )

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
                f"LLM API call timed out after {elapsed_ms}ms (Threshold: {effective_timeout}s)"
            )
            raise LLMTimeoutException(f"LLM call timed out after {elapsed_ms}ms")
        except (LLMServiceException, LLMTimeoutException):
            raise
        except Exception as e:
            elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
            err_str = str(e)
            if (
                "429" in err_str
                or "ResourceExhausted" in err_str
                or "quota" in err_str.lower()
            ):
                cooldown_secs = float(
                    getattr(settings, "RATE_LIMIT_COOLDOWN_SECONDS", 60)
                )
                self.cooldown_until = time.time() + cooldown_secs
                logger.warning(
                    f"[Cost-Guard] Rate limit 429 kích hoạt. Khóa gọi AI trong {int(cooldown_secs)} giây."
                )
                raise LLMServiceException("FREE_TIER_RATE_LIMIT_COOLDOWN")
            logger.error(
                f"LLM API execution error after {elapsed_ms}ms: {str(e)}", exc_info=True
            )
            raise LLMServiceException(f"LLM execution failed: {str(e)}")

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
        if self.api_keys:
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

                thinking_cfg = types.ThinkingConfig(thinking_budget=0)
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
                try:
                    response = self._client.models.generate_content(
                        model=self.model_name,
                        contents=clean_prompt,
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
                            contents=clean_prompt,
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
                response = self._client.generate_content(
                    clean_prompt, generation_config=generation_config
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
            f"{system_prompt or SYSTEM_INSTRUCTION}\n\n"
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
        except (LLMServiceException, LLMTimeoutException):
            raise
        except asyncio.TimeoutError:
            elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
            raise LLMTimeoutException(
                f"Structured LLM call timed out after {elapsed_ms}ms"
            )
        except Exception as exc:
            err_str = str(exc)
            if (
                "429" in err_str
                or "ResourceExhausted" in err_str
                or "quota" in err_str.lower()
            ):
                cooldown_secs = float(
                    getattr(settings, "RATE_LIMIT_COOLDOWN_SECONDS", 60)
                )
                self.cooldown_until = time.time() + cooldown_secs
                raise LLMServiceException("FREE_TIER_RATE_LIMIT_COOLDOWN")
            raise LLMServiceException(f"Structured output call failed: {err_str}")

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
        words = raw_text.split(" ")
        for idx, word in enumerate(words):
            suffix = " " if idx < len(words) - 1 else ""
            yield f"{word}{suffix}"
            await asyncio.sleep(0.005)


llm_service = LLMService()
