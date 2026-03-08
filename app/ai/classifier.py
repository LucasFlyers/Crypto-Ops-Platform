"""
app/ai/classifier.py
─────────────────────
AI Classification Engine.
Orchestrates: prompt building → LLM call → output validation → retry handling.

Retry strategy:
  Attempt 1: Normal prompt
  Attempt 2: Add explicit format reminder to prompt
  Attempt 3: Simplified prompt (reduce chance of confusion)
  After 3 failures: Return a safe fallback classification (do not crash pipeline)
"""

import json
from datetime import datetime, timezone

from pydantic import ValidationError
from tenacity import retry, stop_after_attempt, wait_exponential, RetryError

from app.ai.client import OpenAIClient, AIClientError, AIResponseParseError, get_ai_client
from app.ai.prompts import SYSTEM_PROMPT, build_classification_prompt, build_historical_context
from app.ai.schemas import AIClassificationOutput
from app.config import settings
from app.utils.logging import get_logger

logger = get_logger(__name__)

# Fallback classification used when AI is unavailable
FALLBACK_CLASSIFICATION = AIClassificationOutput(
    category="general_inquiry",
    priority="medium",
    fraud_score=0.0,
    reason="AI classification unavailable — default classification applied. Manual review required.",
)


class ClassificationEngine:
    """
    Orchestrates AI ticket classification with retry logic and fallback.
    """

    def __init__(self, client: OpenAIClient | None = None) -> None:
        self._client = client or get_ai_client()

    def classify(
        self,
        user_id: str,
        wallet_address: str | None,
        transaction_id: str | None,
        message: str,
        ticket_timestamp: datetime | None = None,
        historical_context_data: dict | None = None,
    ) -> tuple[AIClassificationOutput, str]:
        """
        Classify a ticket using the AI engine.

        Args:
            user_id: Ticket submitter
            wallet_address: Optional wallet
            transaction_id: Optional transaction
            message: User's issue description
            ticket_timestamp: When the event occurred
            historical_context_data: Dict with complaint_count, failed_tx_count, etc.

        Returns:
            Tuple of (classification_output, model_name_used)
        """
        if ticket_timestamp is None:
            ticket_timestamp = datetime.now(timezone.utc)

        # Build historical context string if data provided
        historical_context = None
        if historical_context_data:
            historical_context = build_historical_context(
                complaint_count=historical_context_data.get("complaint_count", 0),
                failed_tx_count=historical_context_data.get("failed_tx_count", 0),
                prior_fraud_flags=historical_context_data.get("prior_fraud_flags", 0),
            )

        user_prompt = build_classification_prompt(
            user_id=user_id,
            wallet_address=wallet_address,
            transaction_id=transaction_id,
            message=message,
            ticket_timestamp=ticket_timestamp,
            historical_context=historical_context,
        )

        try:
            result = self._classify_with_retry(user_prompt)
            logger.info(
                "classification_success",
                user_id=user_id,
                category=result.category,
                priority=result.priority,
                fraud_score=result.fraud_score,
            )
            return result, settings.ai_model

        except Exception as e:
            logger.error(
                "classification_failed_using_fallback",
                user_id=user_id,
                error=str(e),
                exc_info=True,
            )
            return FALLBACK_CLASSIFICATION, f"{settings.ai_model}:fallback"

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    def _classify_with_retry(self, user_prompt: str) -> AIClassificationOutput:
        """
        Inner classification with retry.
        Each attempt may enhance the prompt with format reminders.
        tenacity tracks attempt count internally.
        """
        try:
            raw_dict = self._client.complete_json(
                system_prompt=SYSTEM_PROMPT,
                user_message=user_prompt,
            )
        except AIResponseParseError as e:
            # Not valid JSON — retry will kick in
            logger.warning("ai_invalid_json", error=str(e))
            raise

        try:
            return AIClassificationOutput.model_validate(raw_dict)
        except ValidationError as e:
            logger.warning(
                "ai_schema_validation_failed",
                errors=e.errors(),
                raw_dict=raw_dict,
            )
            raise AIResponseParseError(
                f"AI output failed schema validation: {e}"
            ) from e


# Module-level engine instance
_engine: ClassificationEngine | None = None


def get_classification_engine() -> ClassificationEngine:
    """Get the shared classification engine instance."""
    global _engine
    if _engine is None:
        _engine = ClassificationEngine()
    return _engine
