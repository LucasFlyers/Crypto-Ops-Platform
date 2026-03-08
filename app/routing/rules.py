"""
app/routing/rules.py
─────────────────────
Routing rule definitions.
Rules are evaluated in priority order — first match wins.
Each rule is documented with its rationale.

Rule evaluation is deterministic and auditable:
  The `rule_id` is stored in the routing table for compliance review.
"""

from dataclasses import dataclass
from typing import Callable

from app.ai.schemas import AIClassificationOutput
from app.fraud.scorer import WalletRiskScore
from app.config import settings


@dataclass
class RoutingDecision:
    """The outcome of routing rule evaluation."""
    assigned_team: str
    severity_level: str        # critical | high | medium | low
    rule_matched: str          # Rule ID for audit trail


# ── Rule Definitions ──────────────────────────────────────────────────────────

def evaluate_routing_rules(
    classification: AIClassificationOutput,
    risk_score: WalletRiskScore | None,
) -> RoutingDecision:
    """
    Evaluate routing rules in priority order.
    Returns the first matching rule's RoutingDecision.

    Rules are ordered by: severity, specificity, team expertise.
    If no rule matches, falls back to customer_support (safe default).
    """
    fraud_score = risk_score.composite_score if risk_score else classification.fraud_score
    category = classification.category
    priority = classification.priority

    # ── Rule 1: Critical fraud — immediate compliance escalation ──
    # Composite fraud score from engine (more reliable than AI score alone)
    if fraud_score >= settings.fraud_high_risk_threshold:
        return RoutingDecision(
            assigned_team="compliance_team",
            severity_level="critical",
            rule_matched="RULE_001_HIGH_FRAUD_SCORE",
        )

    # ── Rule 2: Fraud report — always compliance ──────────────────
    if category == "fraud_report":
        return RoutingDecision(
            assigned_team="compliance_team",
            severity_level="high",
            rule_matched="RULE_002_FRAUD_REPORT_CATEGORY",
        )

    # ── Rule 3: Suspicious transaction — fraud investigation ──────
    if category == "suspicious_transaction":
        return RoutingDecision(
            assigned_team="fraud_investigation",
            severity_level="high",
            rule_matched="RULE_003_SUSPICIOUS_TRANSACTION",
        )

    # ── Rule 4: Wallet/account security issues → security team ────
    if category in ("wallet_access", "account_access"):
        severity = "high" if priority in ("critical", "high") else "medium"
        return RoutingDecision(
            assigned_team="security_team",
            severity_level=severity,
            rule_matched="RULE_004_WALLET_ACCOUNT_ACCESS",
        )

    # ── Rule 5: High priority withdrawal — technical ops ──────────
    if category == "withdrawal_issue" and priority in ("critical", "high"):
        return RoutingDecision(
            assigned_team="technical_operations",
            severity_level=priority,
            rule_matched="RULE_005_HIGH_PRIORITY_WITHDRAWAL",
        )

    # ── Rule 6: Transaction failure — technical ops ───────────────
    if category == "transaction_failure":
        severity = "high" if priority in ("critical", "high") else "medium"
        return RoutingDecision(
            assigned_team="technical_operations",
            severity_level=severity,
            rule_matched="RULE_006_TRANSACTION_FAILURE",
        )

    # ── Rule 7: Medium fraud score — fraud investigation ─────────
    if fraud_score >= settings.fraud_medium_risk_threshold:
        return RoutingDecision(
            assigned_team="fraud_investigation",
            severity_level="medium",
            rule_matched="RULE_007_MEDIUM_FRAUD_SCORE",
        )

    # ── Rule 8: Low priority withdrawal — customer support ────────
    if category == "withdrawal_issue" and priority == "low":
        return RoutingDecision(
            assigned_team="customer_support",
            severity_level="low",
            rule_matched="RULE_008_LOW_PRIORITY_WITHDRAWAL",
        )

    # ── Default: customer support ─────────────────────────────────
    return RoutingDecision(
        assigned_team="customer_support",
        severity_level=priority if priority in ("low", "medium") else "medium",
        rule_matched="RULE_DEFAULT_CUSTOMER_SUPPORT",
    )
