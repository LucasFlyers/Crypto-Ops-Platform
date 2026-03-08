"""
app/routing/engine.py
──────────────────────
Routing Engine orchestrator.
Fetches classification + fraud data, applies rules, persists routing decision.
"""

import uuid

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.ai.schemas import AIClassificationOutput
from app.fraud.scorer import WalletRiskScore, determine_risk_tier
from app.routing.rules import evaluate_routing_rules, RoutingDecision
from app.utils.logging import get_logger

logger = get_logger(__name__)


class RoutingEngine:
    """
    Orchestrates ticket routing to internal teams.
    Runs synchronously inside Celery workers.
    """

    def route_ticket(
        self,
        session: Session,
        ticket_id: uuid.UUID,
        classification: AIClassificationOutput,
        risk_score: WalletRiskScore | None,
    ) -> RoutingDecision:
        """
        Determine and persist the routing decision for a ticket.

        Args:
            session: Active SQLAlchemy session
            ticket_id: The ticket to route
            classification: AI classification output
            risk_score: Fraud engine risk score (may be None if no wallet)

        Returns:
            RoutingDecision with assigned team and severity
        """
        decision = evaluate_routing_rules(classification, risk_score)

        # Persist routing record
        session.execute(
            text("""
                INSERT INTO routing (id, ticket_id, assigned_team, severity_level, rule_matched, resolved, created_at)
                VALUES (gen_random_uuid(), :ticket_id, :team, :severity, :rule, false, NOW())
                ON CONFLICT (ticket_id) DO UPDATE
                  SET assigned_team = EXCLUDED.assigned_team,
                      severity_level = EXCLUDED.severity_level,
                      rule_matched = EXCLUDED.rule_matched
            """),
            {
                "ticket_id": str(ticket_id),
                "team": decision.assigned_team,
                "severity": decision.severity_level,
                "rule": decision.rule_matched,
            },
        )

        # Update ticket status to routed
        session.execute(
            text("""
                UPDATE tickets
                SET status = 'routed', updated_at = NOW()
                WHERE id = :ticket_id
            """),
            {"ticket_id": str(ticket_id)},
        )

        logger.info(
            "ticket_routed",
            ticket_id=str(ticket_id),
            team=decision.assigned_team,
            severity=decision.severity_level,
            rule=decision.rule_matched,
        )

        return decision


_routing_engine: RoutingEngine | None = None


def get_routing_engine() -> RoutingEngine:
    global _routing_engine
    if _routing_engine is None:
        _routing_engine = RoutingEngine()
    return _routing_engine
