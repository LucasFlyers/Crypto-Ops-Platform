"""
app/fraud/rules.py
───────────────────
Fraud detection rule definitions.
Each rule is a pure function: takes wallet data → returns (triggered: bool, score: float, evidence: str).
Rules are independently testable and configurable via settings.

Rule naming convention: RULE_<DESCRIPTION>
"""

from dataclasses import dataclass
from typing import Callable

from app.config import settings


@dataclass
class RuleResult:
    """Result of a single fraud rule evaluation."""
    triggered: bool
    score: float          # Contribution to overall risk score (0.0–1.0)
    flag_type: str        # Maps to fraud_flags.flag_type
    evidence: str         # Human-readable explanation for audit trail


# ── Rule Implementations ──────────────────────────────────────────────────────

def rule_repeated_complaints(
    complaint_count: int,
    window_hours: int = 24,
) -> RuleResult:
    """
    Flag wallets with multiple complaints in a short window.
    3+ complaints = strong indicator of coordinated fraud attempt or compromised account.
    """
    threshold = settings.fraud_max_complaints_per_wallet
    triggered = complaint_count >= threshold

    if complaint_count == 0:
        score = 0.0
    elif complaint_count < threshold:
        score = 0.2 * (complaint_count / threshold)
    else:
        # Scale: threshold=3 → 0.5, 2x threshold → 0.8, cap at 0.9
        score = min(0.5 + (0.1 * (complaint_count - threshold)), 0.9)

    return RuleResult(
        triggered=triggered,
        score=round(score, 2),
        flag_type="repeated_complaints",
        evidence=(
            f"{complaint_count} complaint(s) filed against this wallet "
            f"in the last {window_hours}h (threshold: {threshold})"
        ),
    )


def rule_high_tx_failure_rate(
    failed_tx_count: int,
    window_hours: int = 24,
) -> RuleResult:
    """
    Flag wallets with high transaction failure counts.
    Repeated failures suggest: probing attacks, money mule activity, or bot behavior.
    """
    threshold = settings.fraud_max_failed_tx_per_wallet
    triggered = failed_tx_count >= threshold

    if failed_tx_count == 0:
        score = 0.0
    elif failed_tx_count < threshold:
        score = 0.15 * (failed_tx_count / threshold)
    else:
        score = min(0.4 + (0.08 * (failed_tx_count - threshold)), 0.8)

    return RuleResult(
        triggered=triggered,
        score=round(score, 2),
        flag_type="high_tx_failure_rate",
        evidence=(
            f"{failed_tx_count} failed transaction(s) from wallet "
            f"in the last {window_hours}h (threshold: {threshold})"
        ),
    )


def rule_multi_account_wallet(unique_user_count: int) -> RuleResult:
    """
    Flag wallets referenced by multiple different user accounts.
    Legitimate wallets are rarely shared across accounts.
    Multiple accounts = potential account farming or money mule network.
    """
    triggered = unique_user_count > 1

    if unique_user_count <= 1:
        score = 0.0
    elif unique_user_count == 2:
        score = 0.3  # Possibly shared (family/business) — moderate risk
    elif unique_user_count <= 4:
        score = 0.6  # Unusual, likely suspicious
    else:
        score = 0.85  # High confidence: coordinated fraud

    return RuleResult(
        triggered=triggered,
        score=round(score, 2),
        flag_type="multi_account_wallet",
        evidence=(
            f"Wallet referenced by {unique_user_count} different user accounts"
        ),
    )


def rule_linked_flagged_wallet(
    linked_flagged_count: int,
) -> RuleResult:
    """
    Flag wallets that have transacted with previously flagged wallets.
    Network propagation of known bad actors.
    """
    triggered = linked_flagged_count > 0

    score = 0.0
    if linked_flagged_count == 1:
        score = 0.4
    elif linked_flagged_count <= 3:
        score = 0.65
    elif linked_flagged_count > 3:
        score = 0.85

    return RuleResult(
        triggered=triggered,
        score=round(score, 2),
        flag_type="linked_flagged_wallet",
        evidence=(
            f"Wallet has transacted with {linked_flagged_count} previously flagged wallet(s)"
        ),
    )


def rule_ai_high_fraud_score(ai_fraud_score: float) -> RuleResult:
    """
    Elevate AI-detected fraud probability into a rule-based flag.
    Bridges AI and rule-based systems.
    """
    threshold = settings.fraud_medium_risk_threshold
    triggered = ai_fraud_score >= threshold

    return RuleResult(
        triggered=triggered,
        score=round(ai_fraud_score, 2),
        flag_type="ai_high_fraud_score",
        evidence=(
            f"AI classifier assigned fraud_score={ai_fraud_score:.2f} "
            f"(threshold: {threshold})"
        ),
    )


# ── Rule Registry ─────────────────────────────────────────────────────────────

ALL_RULES: list[str] = [
    "repeated_complaints",
    "high_tx_failure_rate",
    "multi_account_wallet",
    "linked_flagged_wallet",
    "ai_high_fraud_score",
]
