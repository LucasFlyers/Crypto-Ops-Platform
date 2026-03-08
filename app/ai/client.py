"""
app/ai/client.py
─────────────────
OpenAI API client wrapper.
Handles: authentication, timeouts, error normalization.
All AI calls go through this single interface — swap providers here if needed.
"""

import json
from typing import Any

from openai import OpenAI, RateLimitError, APITimeoutError, APIError

from app.config import settings
from app.utils.logging import get_logger

logger = get_logger(__name__)


class AIClientError(Exception):
    """Raised when the AI API call fails after all retries."""
    pass


class AIResponseParseError(Exception):
    """Raised when the AI response cannot be parsed as expected JSON."""
    pass


class OpenAIClient:
    """
    Thin wrapper around the OpenAI Python SDK.
    Provides a clean interface for the classification engine.
    """

    def __init__(self) -> None:
        self._client = OpenAI(
            api_key=settings.openai_api_key,
            timeout=settings.ai_timeout_seconds,
        )
        self.model = settings.ai_model
        self.max_tokens = settings.ai_max_tokens

    def complete(
        self,
        system_prompt: str,
        user_message: str,
        temperature: float = 0.1,
    ) -> str:
        """
        Send a completion request to OpenAI.

        Args:
            system_prompt: System instructions
            user_message: The user-facing prompt content
            temperature: Low temperature (0.1) for consistent, deterministic outputs

        Returns:
            Raw text response

        Raises:
            AIClientError: On API errors
        """
        logger.info(
            "ai_request_sent",
            model=self.model,
            user_message_length=len(user_message),
        )

        try:
            response = self._client.chat.completions.create(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=temperature,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
            )

            raw_text = response.choices[0].message.content

            logger.info(
                "ai_response_received",
                model=self.model,
                input_tokens=response.usage.prompt_tokens,
                output_tokens=response.usage.completion_tokens,
                response_length=len(raw_text),
            )

            return raw_text

        except RateLimitError as e:
            logger.warning("ai_rate_limit", error=str(e))
            raise AIClientError(f"Rate limited by AI API: {e}") from e
        except APITimeoutError as e:
            logger.warning("ai_timeout", error=str(e))
            raise AIClientError(f"AI API timeout: {e}") from e
        except APIError as e:
            logger.error("ai_api_error", error=str(e), status_code=getattr(e, "status_code", None))
            raise AIClientError(f"AI API error: {e}") from e

    def complete_json(
        self,
        system_prompt: str,
        user_message: str,
    ) -> dict[str, Any]:
        """
        Send a completion request expecting JSON response.
        Uses OpenAI's JSON mode for reliable structured output.
        Strips markdown code fences if present.

        Returns:
            Parsed dict from JSON response

        Raises:
            AIResponseParseError: If response is not valid JSON
        """
        logger.info(
            "ai_json_request_sent",
            model=self.model,
        )

        try:
            response = self._client.chat.completions.create(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=0.1,
                response_format={"type": "json_object"},  # OpenAI JSON mode
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
            )

            raw_text = response.choices[0].message.content

            logger.info(
                "ai_response_received",
                model=self.model,
                input_tokens=response.usage.prompt_tokens,
                output_tokens=response.usage.completion_tokens,
            )

        except RateLimitError as e:
            raise AIClientError(f"Rate limited: {e}") from e
        except APITimeoutError as e:
            raise AIClientError(f"Timeout: {e}") from e
        except APIError as e:
            raise AIClientError(f"API error: {e}") from e

        # Strip markdown code fences if present (defensive)
        cleaned = raw_text.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            cleaned = "\n".join(lines[1:-1]).strip()

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            logger.warning(
                "ai_json_parse_error",
                raw_response=raw_text[:500],
                error=str(e),
            )
            raise AIResponseParseError(
                f"AI response is not valid JSON: {e}\nRaw: {raw_text[:200]}"
            ) from e


# Module-level singleton — created once
_client: OpenAIClient | None = None


def get_ai_client() -> OpenAIClient:
    """Get the shared AI client instance."""
    global _client
    if _client is None:
        _client = OpenAIClient()
    return _client
