"""
tests/test_fraud/test_rules.py
────────────────────────────────
Unit tests for fraud detection rules and scoring.
Rules are pure functions — easy to test without DB.
"""

import pytest

from app.fraud.rules import (
    rule_repeated_complaints,
    rule_high_tx_failure_rate,
    rule_multi_account_wallet,
    rule_linked_flagged_wallet,
    rule_ai_high_fraud_score,
)
from app.fraud.scorer import compute_composite_score, determine_risk_tier, build_wallet_risk_score


# ── repeated_complaints ───────────────────────────────────────────────────────

class TestRepeatedComplaintsRule:
    def test_no_complaints(self):
        result = rule_repeated_complaints(complaint_count=0)
        assert result.triggered is False
        assert result.score == 0.0

    def test_below_threshold(self):
        result = rule_repeated_complaints(complaint_count=2)
        assert result.triggered is False
        assert 0.0 < result.score < 0.5

    def test_at_threshold(self):
        result = rule_repeated_complaints(complaint_count=3)
        assert result.triggered is True
        assert result.score >= 0.5

    def test_above_threshold(self):
        result = rule_repeated_complaints(complaint_count=10)
        assert result.triggered is True
        assert result.score <= 0.9  # Capped

    def test_flag_type(self):
        result = rule_repeated_complaints(complaint_count=5)
        assert result.flag_type == "repeated_complaints"

    def test_evidence_contains_count(self):
        result = rule_repeated_complaints(complaint_count=5)
        assert "5" in result.evidence


# ── multi_account_wallet ──────────────────────────────────────────────────────

class TestMultiAccountWalletRule:
    def test_single_user(self):
        result = rule_multi_account_wallet(unique_user_count=1)
        assert result.triggered is False
        assert result.score == 0.0

    def test_two_users(self):
        result = rule_multi_account_wallet(unique_user_count=2)
        assert result.triggered is True
        assert result.score == 0.3  # Moderate risk

    def test_many_users(self):
        result = rule_multi_account_wallet(unique_user_count=10)
        assert result.triggered is True
        assert result.score >= 0.85  # High confidence fraud


# ── ai_high_fraud_score ───────────────────────────────────────────────────────

class TestAIFraudScoreRule:
    def test_low_score_not_triggered(self):
        result = rule_ai_high_fraud_score(ai_fraud_score=0.2)
        assert result.triggered is False

    def test_medium_threshold(self):
        result = rule_ai_high_fraud_score(ai_fraud_score=0.4)
        assert result.triggered is True

    def test_high_score(self):
        result = rule_ai_high_fraud_score(ai_fraud_score=0.9)
        assert result.triggered is True
        assert result.score == 0.9


# ── Composite Scoring ─────────────────────────────────────────────────────────

class TestCompositeScoring:
    def test_no_triggered_rules(self):
        results = [
            rule_repeated_complaints(0),
            rule_multi_account_wallet(1),
            rule_ai_high_fraud_score(0.1),
        ]
        score = compute_composite_score(results)
        assert score == 0.0

    def test_single_rule_triggered(self):
        results = [
            rule_repeated_complaints(5),   # Score ~0.7
            rule_multi_account_wallet(1),   # Not triggered
        ]
        score = compute_composite_score(results)
        assert score > 0.0
        assert score <= 1.0

    def test_multiple_rules_compound(self):
        """Multiple triggered rules should result in higher composite score."""
        single_result = [rule_repeated_complaints(5)]
        multi_results = [
            rule_repeated_complaints(5),
            rule_multi_account_wallet(3),
            rule_ai_high_fraud_score(0.7),
        ]
        single_score = compute_composite_score(single_result)
        multi_score = compute_composite_score(multi_results)
        assert multi_score > single_score

    def test_score_capped_at_1(self):
        """Composite score should never exceed 1.0."""
        results = [
            rule_repeated_complaints(100),
            rule_multi_account_wallet(50),
            rule_linked_flagged_wallet(20),
            rule_ai_high_fraud_score(1.0),
            rule_high_tx_failure_rate(100),
        ]
        score = compute_composite_score(results)
        assert score <= 1.0


# ── Risk Tier ─────────────────────────────────────────────────────────────────

class TestRiskTier:
    def test_clean(self):
        assert determine_risk_tier(0.0) == "clean"
        assert determine_risk_tier(0.19) == "clean"

    def test_low(self):
        assert determine_risk_tier(0.2) == "low"
        assert determine_risk_tier(0.39) == "low"

    def test_medium(self):
        assert determine_risk_tier(0.4) == "medium"

    def test_high(self):
        assert determine_risk_tier(0.6) == "high"

    def test_critical(self):
        assert determine_risk_tier(0.8) == "critical"
        assert determine_risk_tier(1.0) == "critical"
