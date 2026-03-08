"""
app/workers/tasks.py
─────────────────────
Celery task definitions for the async processing pipeline.

Pipeline:
  classify_ticket_task → fraud_scan_task → route_ticket_task

Each task:
  1. Fetches required data from DB
  2. Performs its work
  3. Updates DB state
  4. Dispatches next task in pipeline
  5. Handles errors with structured logging + retry
"""

import uuid
from datetime import datetime, timezone

from celery import Task
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.workers.celery_app import celery_app
from app.config import settings
from app.utils.logging import get_logger, configure_logging

configure_logging()
logger = get_logger(__name__)


# ── Helper: get synchronous DB session ───────────────────────────────────────

def _get_sync_session() -> Session:
    """Create a synchronous SQLAlchemy session for use in Celery tasks."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    engine = create_engine(settings.database_url_sync, pool_pre_ping=True)
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    return SessionLocal()


# ── Task 1: AI Classification ─────────────────────────────────────────────────

@celery_app.task(
    name="app.workers.tasks.classify_ticket_task",
    bind=True,
    max_retries=3,
    default_retry_delay=5,
    queue="classification",
)
def classify_ticket_task(self: Task, ticket_id: str) -> dict:
    """
    Task 1 in pipeline: Classify ticket with AI.

    Fetches ticket from DB, calls AI classification engine,
    persists classification result, dispatches fraud scan task.
    """
    logger.info("classify_ticket_task_started", ticket_id=ticket_id)

    session = _get_sync_session()
    try:
        # ── Fetch ticket ─────────────────────────────────────────
        ticket_row = session.execute(
            text("SELECT * FROM tickets WHERE id = :id"),
            {"id": ticket_id},
        ).fetchone()

        if not ticket_row:
            logger.error("classify_ticket_task_ticket_not_found", ticket_id=ticket_id)
            return {"status": "error", "reason": "ticket_not_found"}

        # ── Update status to 'classifying' ───────────────────────
        session.execute(
            text("UPDATE tickets SET status = 'classifying', updated_at = NOW() WHERE id = :id"),
            {"id": ticket_id},
        )
        session.commit()

        # ── Gather historical context for wallet ──────────────────
        historical_data = {}
        if ticket_row.wallet_address:
            ctx_row = session.execute(
                text("""
                    SELECT
                        COUNT(DISTINCT t.id) as complaint_count,
                        COUNT(DISTINCT ff.id) as prior_fraud_flags
                    FROM tickets t
                    LEFT JOIN fraud_flags ff ON ff.wallet_address = t.wallet_address
                    WHERE t.wallet_address = :wallet
                      AND t.id != :ticket_id
                """),
                {"wallet": ticket_row.wallet_address, "ticket_id": ticket_id},
            ).fetchone()
            if ctx_row:
                historical_data = {
                    "complaint_count": ctx_row.complaint_count or 0,
                    "failed_tx_count": 0,  # Will be computed by fraud engine
                    "prior_fraud_flags": ctx_row.prior_fraud_flags or 0,
                }

        # ── Run AI classification ─────────────────────────────────
        from app.ai.classifier import get_classification_engine
        engine = get_classification_engine()

        classification, model_used = engine.classify(
            user_id=ticket_row.user_id,
            wallet_address=ticket_row.wallet_address,
            transaction_id=ticket_row.transaction_id,
            message=ticket_row.message,
            ticket_timestamp=ticket_row.created_at,
            historical_context_data=historical_data if historical_data else None,
        )

        # ── Persist classification ────────────────────────────────
        session.execute(
            text("""
                INSERT INTO classifications
                  (id, ticket_id, category, priority, fraud_score, ai_reasoning, ai_model_used, processed_at)
                VALUES
                  (gen_random_uuid(), :ticket_id, :category, :priority, :fraud_score, :reasoning, :model, NOW())
                ON CONFLICT (ticket_id) DO UPDATE
                  SET category = EXCLUDED.category,
                      priority = EXCLUDED.priority,
                      fraud_score = EXCLUDED.fraud_score,
                      ai_reasoning = EXCLUDED.ai_reasoning,
                      processed_at = NOW()
            """),
            {
                "ticket_id": ticket_id,
                "category": classification.category,
                "priority": classification.priority,
                "fraud_score": classification.fraud_score,
                "reasoning": classification.reason,
                "model": model_used,
            },
        )

        # ── Update ticket status ──────────────────────────────────
        session.execute(
            text("UPDATE tickets SET status = 'classified', updated_at = NOW() WHERE id = :id"),
            {"id": ticket_id},
        )
        session.commit()

        logger.info(
            "classify_ticket_task_complete",
            ticket_id=ticket_id,
            category=classification.category,
            priority=classification.priority,
            fraud_score=classification.fraud_score,
        )

        # ── Dispatch fraud scan (if wallet present) ───────────────
        if ticket_row.wallet_address:
            fraud_scan_task.apply_async(
                args=[ticket_id, ticket_row.wallet_address, classification.fraud_score],
                countdown=1,  # 1 second delay to let DB commit propagate
            )
        else:
            # No wallet — skip fraud scan, go straight to routing
            route_ticket_task.apply_async(
                args=[ticket_id],
                countdown=1,
            )

        return {
            "status": "success",
            "ticket_id": ticket_id,
            "category": classification.category,
            "priority": classification.priority,
        }

    except Exception as exc:
        logger.error(
            "classify_ticket_task_failed",
            ticket_id=ticket_id,
            error=str(exc),
            exc_info=True,
        )
        # Mark ticket as error state
        try:
            session.execute(
                text("UPDATE tickets SET status = 'classification_error', updated_at = NOW() WHERE id = :id"),
                {"id": ticket_id},
            )
            session.commit()
        except Exception:
            pass
        raise self.retry(exc=exc, countdown=2 ** self.request.retries * 5)
    finally:
        session.close()


# ── Task 2: Fraud Scan ─────────────────────────────────────────────────────────

@celery_app.task(
    name="app.workers.tasks.fraud_scan_task",
    bind=True,
    max_retries=3,
    default_retry_delay=10,
    queue="fraud",
)
def fraud_scan_task(
    self: Task,
    ticket_id: str,
    wallet_address: str,
    ai_fraud_score: float,
) -> dict:
    """
    Task 2 in pipeline: Run fraud detection on wallet.

    Evaluates all fraud rules, computes composite risk score,
    persists fraud flags if triggered, dispatches routing task.
    """
    logger.info(
        "fraud_scan_task_started",
        ticket_id=ticket_id,
        wallet=wallet_address[:16] + "...",
    )

    session = _get_sync_session()
    try:
        # Update status
        session.execute(
            text("UPDATE tickets SET status = 'fraud_checking', updated_at = NOW() WHERE id = :id"),
            {"id": ticket_id},
        )
        session.commit()

        # Run fraud analysis
        from app.fraud.engine import get_fraud_engine
        fraud_engine = get_fraud_engine()
        risk_score = fraud_engine.analyze_wallet(
            wallet_address=wallet_address,
            ticket_id=uuid.UUID(ticket_id),
            ai_fraud_score=ai_fraud_score,
        )

        # Update status
        session.execute(
            text("UPDATE tickets SET status = 'fraud_checked', updated_at = NOW() WHERE id = :id"),
            {"id": ticket_id},
        )
        session.commit()

        logger.info(
            "fraud_scan_task_complete",
            ticket_id=ticket_id,
            composite_score=risk_score.composite_score,
            risk_tier=risk_score.risk_tier,
        )

        # Dispatch routing task
        route_ticket_task.apply_async(
            args=[ticket_id],
            countdown=1,
        )

        return {
            "status": "success",
            "ticket_id": ticket_id,
            "composite_fraud_score": risk_score.composite_score,
            "risk_tier": risk_score.risk_tier,
        }

    except Exception as exc:
        logger.error(
            "fraud_scan_task_failed",
            ticket_id=ticket_id,
            error=str(exc),
            exc_info=True,
        )
        # On fraud scan failure, still proceed to routing with AI score only
        logger.warning(
            "fraud_scan_failed_proceeding_to_routing",
            ticket_id=ticket_id,
        )
        route_ticket_task.apply_async(args=[ticket_id], countdown=2)
        return {"status": "error_fallback", "ticket_id": ticket_id}
    finally:
        session.close()


# ── Task 3: Route Ticket ──────────────────────────────────────────────────────

@celery_app.task(
    name="app.workers.tasks.route_ticket_task",
    bind=True,
    max_retries=3,
    default_retry_delay=5,
    queue="routing",
)
def route_ticket_task(self: Task, ticket_id: str) -> dict:
    """
    Task 3 in pipeline: Route ticket to appropriate internal team.

    Fetches classification + fraud data, applies routing rules,
    persists routing decision, marks ticket as fully processed.
    """
    logger.info("route_ticket_task_started", ticket_id=ticket_id)

    session = _get_sync_session()
    try:
        # ── Fetch classification ──────────────────────────────────
        cls_row = session.execute(
            text("SELECT * FROM classifications WHERE ticket_id = :id"),
            {"id": ticket_id},
        ).fetchone()

        if not cls_row:
            logger.error("route_ticket_no_classification", ticket_id=ticket_id)
            raise ValueError(f"No classification found for ticket {ticket_id}")

        # Reconstruct classification object
        from app.ai.schemas import AIClassificationOutput
        classification = AIClassificationOutput(
            category=cls_row.category,
            priority=cls_row.priority,
            fraud_score=cls_row.fraud_score,
            reason=cls_row.ai_reasoning,
        )

        # ── Fetch wallet + fraud score ────────────────────────────
        ticket_row = session.execute(
            text("SELECT wallet_address FROM tickets WHERE id = :id"),
            {"id": ticket_id},
        ).fetchone()

        # Build a minimal WalletRiskScore from DB data if wallet exists
        risk_score = None
        if ticket_row and ticket_row.wallet_address:
            # Get aggregate fraud score for wallet
            fraud_agg = session.execute(
                text("""
                    SELECT COALESCE(MAX(flag_score), 0) as max_score,
                           COUNT(*) as flag_count
                    FROM fraud_flags
                    WHERE wallet_address = :wallet
                """),
                {"wallet": ticket_row.wallet_address},
            ).fetchone()

            if fraud_agg and fraud_agg.flag_count > 0:
                from app.fraud.scorer import WalletRiskScore, determine_risk_tier
                composite = min(fraud_agg.max_score, 1.0)
                risk_score = WalletRiskScore(
                    wallet_address=ticket_row.wallet_address,
                    composite_score=composite,
                    triggered_rules=[],
                    all_results=[],
                    risk_tier=determine_risk_tier(composite),
                )

        # ── Apply routing rules ───────────────────────────────────
        from app.routing.engine import get_routing_engine
        routing_engine = get_routing_engine()
        decision = routing_engine.route_ticket(
            session=session,
            ticket_id=uuid.UUID(ticket_id),
            classification=classification,
            risk_score=risk_score,
        )
        session.commit()

        logger.info(
            "route_ticket_task_complete",
            ticket_id=ticket_id,
            team=decision.assigned_team,
            severity=decision.severity_level,
            rule=decision.rule_matched,
        )

        return {
            "status": "success",
            "ticket_id": ticket_id,
            "assigned_team": decision.assigned_team,
            "severity_level": decision.severity_level,
            "rule_matched": decision.rule_matched,
        }

    except Exception as exc:
        logger.error(
            "route_ticket_task_failed",
            ticket_id=ticket_id,
            error=str(exc),
            exc_info=True,
        )
        try:
            session.execute(
                text("UPDATE tickets SET status = 'routing_error', updated_at = NOW() WHERE id = :id"),
                {"id": ticket_id},
            )
            session.commit()
        except Exception:
            pass
        raise self.retry(exc=exc, countdown=2 ** self.request.retries * 5)
    finally:
        session.close()
