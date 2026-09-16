"""Google Gemini 1.5 Flash client wrapper with latency tracking and strict timeout."""

import asyncio
import time
import logging
from typing import Optional, Tuple, Dict, Any

from app.core.config import settings
from app.core.exceptions import LLMTimeoutException, LLMServiceException

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
    """Async Google Gemini 1.5 Flash Service Wrapper."""

    def __init__(self) -> None:
        self.api_key = settings.GEMINI_API_KEY
        self.model_name = settings.LLM_MODEL_NAME
        self.timeout_seconds = settings.LLM_TIMEOUT_SECONDS
        self._client: Any = None
        self._init_client()

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

    async def generate_response(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.2
    ) -> Tuple[str, float]:
        """
        Executes an async generation request with hard 4.0s timeout and latency measurement.
        
        Returns:
            Tuple[str, float]: (generated_text, latency_ms)
            
        Raises:
            LLMTimeoutException: If execution exceeds 4.0s.
            LLMServiceException: If API key is missing or API errors out.
        """
        if not self._client:
            self._init_client()

        if not self._client or not self.api_key:
            raise LLMServiceException("Gemini API key is not configured or client failed to initialize.")

        start_time = time.perf_counter()
        effective_system_prompt = system_prompt or SYSTEM_INSTRUCTION

        try:
            # Wrap asynchronous call within timeout budget (4.0s)
            response_text = await asyncio.wait_for(
                self._execute_api_call(prompt, effective_system_prompt, temperature),
                timeout=self.timeout_seconds
            )
            elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
            return response_text, elapsed_ms

        except asyncio.TimeoutError:
            elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.warning(f"LLM API call timed out after {elapsed_ms}ms (Threshold: {self.timeout_seconds}s)")
            raise LLMTimeoutException(f"LLM call timed out after {elapsed_ms}ms")
        except Exception as e:
            elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.error(f"LLM API execution error after {elapsed_ms}ms: {str(e)}", exc_info=True)
            raise LLMServiceException(f"LLM execution failed: {str(e)}")

    async def _execute_api_call(self, prompt: str, system_prompt: str, temperature: float) -> str:
        """Internal dispatcher executing SDK generation call asynchronously."""
        if self._sdk_type == "genai":
            # google-genai client
            def _sync_call() -> str:
                from google.genai import types
                response = self._client.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=system_prompt,
                        temperature=temperature,
                    )
                )
                return response.text or ""
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


llm_service = LLMService()
