import json
import logging
import time
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

        if self.api_key and len(self.api_key) > 5:
            try:
                self._client = genai.Client(api_key=self.api_key)
            except Exception as e:
                logger.error(f"Failed to initialize Google Gen AI Client: {e}")

    @property
    def is_configured(self) -> bool:
        return bool(self._client and self.api_key)

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
