"""
app/fraud/scorer.py
────────────────────
Aggregates individual rule results into a single wallet risk score.

Scoring methodology:
  - Uses weighted maximum approach (not simple average)
  - The highest individual rule score dominates (worst-case principle)
  - Additional triggered rules provide additive boosting
  - Final score is clamped to [0.0, 1.0]

This is conservative by design: in fraud detection, false negatives
(missing real fraud) are far more costly than false positives.
"""

from dataclasses import dataclass

from app.fraud.rules import RuleResult
from app.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class WalletRiskScore:
    """Aggregated risk assessment for a wallet."""
    wallet_address: str
    composite_score: float           # Final 0.0–1.0 risk score
    triggered_rules: list[RuleResult]  # Rules that fired
    all_results: list[RuleResult]    # All evaluated rules
    risk_tier: str                   # human: clean | low | medium | high | critical

    @property
    def is_flagged(self) -> bool:
        """True if composite score exceeds medium threshold."""
        from app.config import settings
        return self.composite_score >= settings.fraud_medium_risk_threshold

    @property
    def requires_immediate_action(self) -> bool:
        """True if composite score exceeds high threshold."""
        from app.config import settings
        return self.composite_score >= settings.fraud_high_risk_threshold


def compute_composite_score(rule_results: list[RuleResult]) -> float:
    """
    Compute composite risk score from individual rule results.

    Algorithm:
      1. Take the maximum score among all triggered rules (dominant signal)
      2. Add 10% of each additional triggered rule's score (corroboration boost)
      3. Clamp to [0.0, 1.0]

    This means: one very strong signal is sufficient,
    but multiple moderate signals compound appropriately.
    """
    triggered = [r for r in rule_results if r.triggered]

    if not triggered:
        return 0.0

    # Sort by score descending
    sorted_results = sorted(triggered, key=lambda r: r.score, reverse=True)

    # Primary signal: highest individual score
    composite = sorted_results[0].score

    # Corroboration: each additional triggered rule adds 10% of its score
    for result in sorted_results[1:]:
        composite += result.score * 0.10

    return round(min(composite, 1.0), 3)


def determine_risk_tier(score: float) -> str:
    """Map a numeric score to a human-readable risk tier."""
    if score < 0.2:
        return "clean"
    elif score < 0.4:
        return "low"
    elif score < 0.6:
        return "medium"
    elif score < 0.8:
        return "high"
    else:
        return "critical"


def build_wallet_risk_score(
    wallet_address: str,
    rule_results: list[RuleResult],
) -> WalletRiskScore:
    """
    Assemble the full WalletRiskScore from evaluated rules.
    """
    composite = compute_composite_score(rule_results)
    tier = determine_risk_tier(composite)
    triggered = [r for r in rule_results if r.triggered]

    logger.info(
        "wallet_risk_scored",
        wallet=wallet_address[:16] + "...",
        composite_score=composite,
        risk_tier=tier,
        rules_triggered=len(triggered),
    )

    return WalletRiskScore(
        wallet_address=wallet_address,
        composite_score=composite,
        triggered_rules=triggered,
        all_results=rule_results,
        risk_tier=tier,
    )
