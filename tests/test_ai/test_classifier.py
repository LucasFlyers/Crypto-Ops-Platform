"""
tests/test_ai/test_classifier.py
──────────────────────────────────
Unit tests for the AI classification engine.
Mocks the Anthropic client to avoid real API calls in tests.
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from app.ai.classifier import ClassificationEngine, FALLBACK_CLASSIFICATION
from app.ai.client import AnthropicClient, AIResponseParseError
from app.ai.schemas import AIClassificationOutput


def make_mock_client(response_dict: dict) -> AnthropicClient:
    """Create a mock AI client that returns a fixed JSON response."""
    mock_client = MagicMock(spec=AnthropicClient)
    mock_client.complete_json.return_value = response_dict
    return mock_client


class TestClassificationEngine:

    def test_successful_classification(self):
        """Engine returns validated output for a well-formed AI response."""
        mock_response = {
            "category": "withdrawal_issue",
            "priority": "high",
            "fraud_score": 0.35,
            "reason": "User reports 8-hour pending withdrawal, possible backend processing delay",
        }
        client = make_mock_client(mock_response)
        engine = ClassificationEngine(client=client)

        result, model = engine.classify(
            user_id="test_user",
            wallet_address="0x1234",
            transaction_id="TX001",
            message="My withdrawal has been pending for 8 hours",
        )

        assert isinstance(result, AIClassificationOutput)
        assert result.category == "withdrawal_issue"
        assert result.priority == "high"
        assert result.fraud_score == 0.35
        assert len(result.reason) > 0

    def test_invalid_category_triggers_fallback(self):
        """Invalid category in AI response triggers fallback after retries."""
        mock_response = {
            "category": "INVALID_CATEGORY",  # Not in allowed values
            "priority": "high",
            "fraud_score": 0.5,
            "reason": "Some reason here that is long enough",
        }
        client = make_mock_client(mock_response)
        engine = ClassificationEngine(client=client)

        result, model = engine.classify(
            user_id="test_user",
            wallet_address=None,
            transaction_id=None,
            message="Test message that is long enough to pass validation",
        )

        # Should fall back gracefully
        assert result.category == FALLBACK_CLASSIFICATION.category
        assert "fallback" in model

    def test_fraud_score_out_of_range_triggers_fallback(self):
        """fraud_score > 1.0 should fail validation and use fallback."""
        mock_response = {
            "category": "withdrawal_issue",
            "priority": "high",
            "fraud_score": 1.5,  # Invalid: > 1.0
            "reason": "Reason is long enough to pass min length check here",
        }
        client = make_mock_client(mock_response)
        engine = ClassificationEngine(client=client)

        result, model = engine.classify(
            user_id="test_user",
            wallet_address=None,
            transaction_id=None,
            message="Test message that is long enough to pass validation",
        )

        assert "fallback" in model

    def test_invalid_json_triggers_fallback(self):
        """Non-JSON response triggers fallback."""
        client = MagicMock(spec=AnthropicClient)
        client.complete_json.side_effect = AIResponseParseError("not json")

        engine = ClassificationEngine(client=client)

        result, model = engine.classify(
            user_id="test_user",
            wallet_address=None,
            transaction_id=None,
            message="Test message that is long enough to pass validation",
        )

        assert result == FALLBACK_CLASSIFICATION
        assert "fallback" in model

    def test_classification_with_historical_context(self):
        """Historical context is passed to the AI prompt."""
        mock_response = {
            "category": "fraud_report",
            "priority": "critical",
            "fraud_score": 0.85,
            "reason": "Multiple prior complaints indicate coordinated fraud attempt ongoing",
        }
        client = make_mock_client(mock_response)
        engine = ClassificationEngine(client=client)

        result, model = engine.classify(
            user_id="test_user",
            wallet_address="0x1234",
            transaction_id=None,
            message="Someone is using my wallet without my permission to steal funds",
            historical_context_data={
                "complaint_count": 5,
                "failed_tx_count": 3,
                "prior_fraud_flags": 2,
            },
        )

        assert result.category == "fraud_report"
        assert result.fraud_score == 0.85


class TestAIOutputSchema:
    """Test the Pydantic validation layer for AI outputs."""

    def test_valid_output(self):
        output = AIClassificationOutput(
            category="withdrawal_issue",
            priority="high",
            fraud_score=0.5,
            reason="Valid reason that is long enough to pass validation checks here",
        )
        assert output.fraud_score == 0.5

    def test_fraud_score_rounded(self):
        output = AIClassificationOutput(
            category="general_inquiry",
            priority="low",
            fraud_score=0.12345,
            reason="Valid reason that is long enough to pass validation checks here",
        )
        assert output.fraud_score == 0.12  # Rounded to 2 decimal places

    def test_invalid_priority_rejected(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            AIClassificationOutput(
                category="withdrawal_issue",
                priority="URGENT",  # Not in allowed values
                fraud_score=0.5,
                reason="Reason long enough to pass minimum length validation check",
            )
