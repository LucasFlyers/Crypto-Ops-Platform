"""
tests/test_services/test_routing.py
─────────────────────────────────────
Unit tests for routing rule evaluation.
Rules are deterministic — test all branches.
"""

import pytest

from app.ai.schemas import AIClassificationOutput
from app.fraud.scorer import WalletRiskScore, determine_risk_tier
from app.routing.rules import evaluate_routing_rules


def make_classification(
    category: str = "general_inquiry",
    priority: str = "low",
    fraud_score: float = 0.0,
) -> AIClassificationOutput:
    return AIClassificationOutput(
        category=category,
        priority=priority,
        fraud_score=fraud_score,
        reason="Test classification",
    )


def make_risk_score(composite: float) -> WalletRiskScore:
    return WalletRiskScore(
        wallet_address="0xtest",
        composite_score=composite,
        triggered_rules=[],
        all_results=[],
        risk_tier=determine_risk_tier(composite),
    )


class TestRoutingRules:

    def test_rule_001_high_fraud_score_goes_to_compliance(self):
        cls = make_classification(category="withdrawal_issue", fraud_score=0.5)
        risk = make_risk_score(0.8)  # Above high threshold
        decision = evaluate_routing_rules(cls, risk)
        assert decision.assigned_team == "compliance_team"
        assert decision.severity_level == "critical"
        assert decision.rule_matched == "RULE_001_HIGH_FRAUD_SCORE"

    def test_rule_002_fraud_report_goes_to_compliance(self):
        cls = make_classification(category="fraud_report", priority="high")
        decision = evaluate_routing_rules(cls, None)
        assert decision.assigned_team == "compliance_team"
        assert decision.rule_matched == "RULE_002_FRAUD_REPORT_CATEGORY"

    def test_rule_003_suspicious_transaction_goes_to_fraud_investigation(self):
        cls = make_classification(category="suspicious_transaction", priority="high")
        decision = evaluate_routing_rules(cls, None)
        assert decision.assigned_team == "fraud_investigation"
        assert decision.rule_matched == "RULE_003_SUSPICIOUS_TRANSACTION"

    def test_rule_004_wallet_access_goes_to_security_team(self):
        cls = make_classification(category="wallet_access", priority="high")
        decision = evaluate_routing_rules(cls, None)
        assert decision.assigned_team == "security_team"
        assert decision.rule_matched == "RULE_004_WALLET_ACCOUNT_ACCESS"

    def test_rule_004_account_access_goes_to_security_team(self):
        cls = make_classification(category="account_access", priority="medium")
        decision = evaluate_routing_rules(cls, None)
        assert decision.assigned_team == "security_team"

    def test_rule_005_high_priority_withdrawal_goes_to_tech_ops(self):
        cls = make_classification(category="withdrawal_issue", priority="high")
        risk = make_risk_score(0.1)  # Low fraud
        decision = evaluate_routing_rules(cls, risk)
        assert decision.assigned_team == "technical_operations"
        assert decision.severity_level == "high"
        assert decision.rule_matched == "RULE_005_HIGH_PRIORITY_WITHDRAWAL"

    def test_rule_006_transaction_failure_goes_to_tech_ops(self):
        cls = make_classification(category="transaction_failure", priority="medium")
        decision = evaluate_routing_rules(cls, None)
        assert decision.assigned_team == "technical_operations"
        assert decision.rule_matched == "RULE_006_TRANSACTION_FAILURE"

    def test_rule_008_low_withdrawal_goes_to_customer_support(self):
        cls = make_classification(category="withdrawal_issue", priority="low")
        risk = make_risk_score(0.0)
        decision = evaluate_routing_rules(cls, risk)
        assert decision.assigned_team == "customer_support"
        assert decision.rule_matched == "RULE_008_LOW_PRIORITY_WITHDRAWAL"

    def test_default_general_inquiry_goes_to_customer_support(self):
        cls = make_classification(category="general_inquiry", priority="low")
        decision = evaluate_routing_rules(cls, None)
        assert decision.assigned_team == "customer_support"
        assert "DEFAULT" in decision.rule_matched

    def test_rule_priority_order_fraud_beats_wallet_access(self):
        """High fraud score should route to compliance even if category is wallet_access."""
        cls = make_classification(category="wallet_access", priority="high")
        risk = make_risk_score(0.85)  # Critical fraud
        decision = evaluate_routing_rules(cls, risk)
        # Rule 001 (high fraud) should trigger before Rule 004 (wallet_access)
        assert decision.assigned_team == "compliance_team"
        assert decision.rule_matched == "RULE_001_HIGH_FRAUD_SCORE"
