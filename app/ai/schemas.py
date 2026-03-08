"""
app/ai/schemas.py
──────────────────
Pydantic models for AI API structured output validation.
The AI must return exactly this structure — anything else triggers a retry.

category values (extensible):
  withdrawal_issue | wallet_access | suspicious_transaction |
  account_access | transaction_failure | fraud_report | general_inquiry

priority values:
  critical | high | medium | low
"""

from typing import Literal
from pydantic import BaseModel, Field, field_validator


IssueCategory = Literal[
    "withdrawal_issue",
    "wallet_access",
    "suspicious_transaction",
    "account_access",
    "transaction_failure",
    "fraud_report",
    "general_inquiry",
]

PriorityLevel = Literal["critical", "high", "medium", "low"]


class AIClassificationOutput(BaseModel):
    """
    Strict schema for LLM classification output.
    Any deviation causes a validation error, triggering a retry.
    """

    category: IssueCategory = Field(
        ...,
        description="Issue category classification",
    )
    priority: PriorityLevel = Field(
        ...,
        description="Priority level for internal triage",
    )
    fraud_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Probability of fraudulent activity (0.0 = clean, 1.0 = confirmed fraud)",
    )
    reason: str = Field(
        ...,
        min_length=20,
        max_length=1000,
        description="AI reasoning for the classification decision",
    )

    @field_validator("fraud_score")
    @classmethod
    def round_fraud_score(cls, v: float) -> float:
        """Round to 2 decimal places for consistency."""
        return round(v, 2)

    @field_validator("reason")
    @classmethod
    def clean_reason(cls, v: str) -> str:
        return v.strip()
