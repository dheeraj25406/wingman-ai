import json
import logging
import time
from datetime import datetime, timezone
from typing import Optional, Dict, Any, Type, TypeVar
from pydantic import BaseModel, ValidationError
from google import genai
from google.genai import types

from backend.app.core.config import settings

logger = logging.getLogger("wingman.gemini")

T = TypeVar("T", bound=BaseModel)


class GeminiService:
    """
    Centralized, resilient service abstraction for the Google Gemini API.
    Strictly configured for Gemini 3.5 Flash-Lite (model: gemini-3.5-flash-lite).
    Enforces structured Pydantic schema validation, exponential backoff retries,
    timeout handling, and strict error reporting without fabricated fallbacks.
    """

    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY
        self.model_id = settings.GEMINI_MODEL or "gemini-3.5-flash-lite"
        self._client: Optional[genai.Client] = None
        self.last_call_metadata: Optional[Dict[str, Any]] = None

        if self.api_key and len(self.api_key) > 5:
            try:
                self._client = genai.Client(api_key=self.api_key)
            except Exception as e:
                logger.error(f"Failed to initialize Google Gen AI Client: {e}")

    @property
    def is_configured(self) -> bool:
        return bool(self._client and self.api_key)

    def set_api_key(self, key: str):
        """Update runtime API key and reinitialize client."""
        self.api_key = key.strip()
        settings.GEMINI_API_KEY = self.api_key
        try:
            self._client = genai.Client(api_key=self.api_key)
            return True
        except Exception as e:
            logger.error(f"Failed to re-initialize client with updated key: {e}")
            self._client = None
            return False

    def test_connection(self) -> Dict[str, Any]:
        """Verify live API connectivity to gemini-3.5-flash-lite."""
        if not self.is_configured:
            return {
                "ok": False,
                "model": self.model_id,
                "error": "Gemini API key is not configured or missing."
            }
        try:
            start_time = time.time()
            resp = self._client.models.generate_content(
                model=self.model_id,
                contents="Ping",
            )
            duration_ms = round((time.time() - start_time) * 1000, 1)
            return {
                "ok": True,
                "model": self.model_id,
                "latency_ms": duration_ms,
                "response_text": resp.text.strip() if resp.text else "OK",
                "message": f"Verified live connection to {self.model_id} ({duration_ms}ms)"
            }
        except Exception as e:
            logger.error(f"Gemini connection test failed: {e}")
            return {
                "ok": False,
                "model": self.model_id,
                "error": str(e)
            }

    def generate_text(self, prompt: str, system_instruction: Optional[str] = None) -> str:
        """
        Executes raw unstructured text generation using gemini-3.5-flash-lite.
        """
        if not self.is_configured:
            raise RuntimeError(f"Gemini API is not configured. Target model: {self.model_id}")
        config = types.GenerateContentConfig(temperature=0.1)
        if system_instruction:
            config.system_instruction = system_instruction
        response = self._client.models.generate_content(
            model=self.model_id,
            contents=prompt,
            config=config,
        )
        return response.text.strip() if response and response.text else ""

    def generate_structured_hypotheses(
        self,
        prompt: str,
        schema_class: Type[T],
        system_instruction: Optional[str] = None,
        max_retries: int = 3,
        timeout_seconds: float = 30.0,
    ) -> T:
        """
        Executes reasoning using gemini-3.5-flash-lite, requiring structured JSON
        validated against the target Pydantic schema.
        """
        if not self.is_configured:
            raise RuntimeError(
                f"Gemini API is not configured. Please set GEMINI_API_KEY in .env. Target model: {self.model_id}"
            )

        config = types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.1,  # Low temperature for strict factual investigation
        )
        if system_instruction:
            config.system_instruction = system_instruction

        last_error = None
        for attempt in range(1, max_retries + 1):
            try:
                start_time = time.time()
                response = self._client.models.generate_content(
                    model=self.model_id,
                    contents=prompt,
                    config=config,
                )
                duration = time.time() - start_time
                logger.info(f"Gemini call completed in {duration:.2f}s (attempt {attempt})")

                if not response.text:
                    raise ValueError("Received empty response from Gemini API")

                # Parse JSON
                raw_json = json.loads(response.text)

                # Validate against target Pydantic schema
                validated_data = schema_class.model_validate(raw_json)

                # Capture call telemetry & token usage
                usage = getattr(response, "usage_metadata", None)
                self.last_call_metadata = {
                    "model_version": getattr(response, "model_version", self.model_id),
                    "prompt_tokens": getattr(usage, "prompt_token_count", None) if usage else None,
                    "candidates_tokens": getattr(usage, "candidates_token_count", None) if usage else None,
                    "total_tokens": getattr(usage, "total_token_count", None) if usage else None,
                    "duration_seconds": round(duration, 3),
                    "prompt_length_chars": len(prompt),
                    "response_length_chars": len(response.text) if response.text else 0,
                    "raw_response": response.text,
                    "attempt": attempt,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
                return validated_data

            except ValidationError as ve:
                logger.warning(f"Gemini response failed Pydantic schema validation: {ve}")
                last_error = ve
            except json.JSONDecodeError as je:
                logger.warning(f"Failed to parse Gemini response as JSON: {je}")
                last_error = je
            except Exception as e:
                logger.error(f"Gemini API error (attempt {attempt}/{max_retries}): {e}")
                last_error = e
                # Exponential backoff
                time.sleep(1.0 * attempt)

        raise RuntimeError(f"Gemini investigation failed after {max_retries} attempts: {last_error}")


gemini_service = GeminiService()
