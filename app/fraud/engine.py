"""
app/fraud/engine.py
────────────────────
Fraud Detection Engine orchestrator.
Queries historical data, evaluates rules, computes risk scores, persists flags.

This is intentionally synchronous — it runs inside Celery workers,
not inside the async FastAPI request path.
Uses synchronous SQLAlchemy for simplicity in the worker context.
"""

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine, text, select, func
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings
from app.fraud.rules import (
    RuleResult,
    rule_repeated_complaints,
    rule_high_tx_failure_rate,
    rule_multi_account_wallet,
    rule_linked_flagged_wallet,
    rule_ai_high_fraud_score,
)
from app.fraud.scorer import WalletRiskScore, build_wallet_risk_score
from app.utils.logging import get_logger

logger = get_logger(__name__)

# Synchronous engine for Celery workers
_sync_engine = None


def _get_sync_engine():
    global _sync_engine
    if _sync_engine is None:
        _sync_engine = create_engine(
            settings.database_url_sync,
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True,
        )
    return _sync_engine


def _get_sync_session() -> Session:
    engine = _get_sync_engine()
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    return SessionLocal()


class FraudDetectionEngine:
    """
    Orchestrates fraud detection for a given wallet address.
    Queries DB for behavioral patterns, evaluates rules, persists flags.
    """

    def analyze_wallet(
        self,
        wallet_address: str,
        ticket_id: uuid.UUID,
        ai_fraud_score: float = 0.0,
    ) -> WalletRiskScore:
        """
        Run full fraud analysis for a wallet.

        Args:
            wallet_address: The wallet to analyze
            ticket_id: The triggering ticket (for logging)
            ai_fraud_score: The fraud score from AI classification

        Returns:
            WalletRiskScore with composite score and rule results
        """
        logger.info(
            "fraud_analysis_started",
            wallet=wallet_address[:16] + "..." if len(wallet_address) > 16 else wallet_address,
            ticket_id=str(ticket_id),
        )

        with _get_sync_session() as session:
            # Gather behavioral data
            wallet_data = self._gather_wallet_data(session, wallet_address)

            # Evaluate all rules
            rule_results = self._evaluate_rules(wallet_data, ai_fraud_score)

            # Compute composite score
            risk_score = build_wallet_risk_score(wallet_address, rule_results)

            # Persist flags for triggered rules
            if risk_score.is_flagged:
                self._persist_fraud_flags(session, wallet_address, risk_score.triggered_rules)
                session.commit()

            logger.info(
                "fraud_analysis_complete",
                wallet=wallet_address[:16] + "...",
                composite_score=risk_score.composite_score,
                risk_tier=risk_score.risk_tier,
                flags_created=len(risk_score.triggered_rules) if risk_score.is_flagged else 0,
            )

            return risk_score

    def _gather_wallet_data(self, session: Session, wallet_address: str) -> dict:
        """
        Query historical data for fraud rule inputs.
        All queries scoped to the configured time window.
        """
        window_start = datetime.now(timezone.utc) - timedelta(
            hours=settings.fraud_flag_window_hours
        )

        # 1. Count recent complaints for this wallet
        complaint_count_row = session.execute(
            text("""
                SELECT COUNT(*) as cnt
                FROM tickets
                WHERE wallet_address = :wallet
                  AND created_at >= :window_start
            """),
            {"wallet": wallet_address, "window_start": window_start},
        ).fetchone()
        complaint_count = complaint_count_row.cnt if complaint_count_row else 0

        # 2. Count failed transactions (tickets about transaction failures)
        failed_tx_row = session.execute(
            text("""
                SELECT COUNT(*) as cnt
                FROM tickets t
                JOIN classifications c ON c.ticket_id = t.id
                WHERE t.wallet_address = :wallet
                  AND c.category IN ('transaction_failure', 'withdrawal_issue')
                  AND t.created_at >= :window_start
            """),
            {"wallet": wallet_address, "window_start": window_start},
        ).fetchone()
        failed_tx_count = failed_tx_row.cnt if failed_tx_row else 0

        # 3. Count distinct user_ids referencing this wallet
        unique_users_row = session.execute(
            text("""
                SELECT COUNT(DISTINCT user_id) as cnt
                FROM tickets
                WHERE wallet_address = :wallet
            """),
            {"wallet": wallet_address},
        ).fetchone()
        unique_user_count = unique_users_row.cnt if unique_users_row else 1

        # 4. Count existing fraud flags for this wallet
        existing_flags_row = session.execute(
            text("""
                SELECT COUNT(*) as cnt
                FROM fraud_flags
                WHERE wallet_address = :wallet
            """),
            {"wallet": wallet_address},
        ).fetchone()
        linked_flagged_count = existing_flags_row.cnt if existing_flags_row else 0

        return {
            "complaint_count": complaint_count,
            "failed_tx_count": failed_tx_count,
            "unique_user_count": unique_user_count,
            "linked_flagged_count": linked_flagged_count,
        }

    def _evaluate_rules(
        self, wallet_data: dict, ai_fraud_score: float
    ) -> list[RuleResult]:
        """Evaluate all fraud rules against wallet data."""
        return [
            rule_repeated_complaints(
                complaint_count=wallet_data["complaint_count"],
                window_hours=settings.fraud_flag_window_hours,
            ),
            rule_high_tx_failure_rate(
                failed_tx_count=wallet_data["failed_tx_count"],
                window_hours=settings.fraud_flag_window_hours,
            ),
            rule_multi_account_wallet(
                unique_user_count=wallet_data["unique_user_count"],
            ),
            rule_linked_flagged_wallet(
                linked_flagged_count=wallet_data["linked_flagged_count"],
            ),
            rule_ai_high_fraud_score(
                ai_fraud_score=ai_fraud_score,
            ),
        ]

    def _persist_fraud_flags(
        self,
        session: Session,
        wallet_address: str,
        triggered_rules: list[RuleResult],
    ) -> None:
        """Insert fraud flag records for all triggered rules."""
        for rule in triggered_rules:
            session.execute(
                text("""
                    INSERT INTO fraud_flags (id, wallet_address, flag_type, flag_score, evidence, created_at)
                    VALUES (gen_random_uuid(), :wallet, :flag_type, :flag_score, :evidence, NOW())
                """),
                {
                    "wallet": wallet_address,
                    "flag_type": rule.flag_type,
                    "flag_score": rule.score,
                    "evidence": rule.evidence,
                },
            )
            logger.info(
                "fraud_flag_created",
                wallet=wallet_address[:16] + "...",
                flag_type=rule.flag_type,
                score=rule.score,
            )


# Module-level engine instance
_fraud_engine: FraudDetectionEngine | None = None


def get_fraud_engine() -> FraudDetectionEngine:
    global _fraud_engine
    if _fraud_engine is None:
        _fraud_engine = FraudDetectionEngine()
    return _fraud_engine
