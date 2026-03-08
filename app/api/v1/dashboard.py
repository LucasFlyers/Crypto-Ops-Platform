"""
app/api/v1/dashboard.py
────────────────────────
Dashboard data API — feeds the monitoring dashboard.
All queries are optimized aggregations using the indexed columns.
"""

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.config import settings
from app.utils.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/stats", summary="Full dashboard statistics")
async def get_dashboard_stats(db: AsyncSession = Depends(get_db)) -> dict:
    """
    Single endpoint that returns all stats needed for the monitoring dashboard.
    Optimized: runs parallel queries, single round trip to the client.
    """

    # ── Ticket stats ──────────────────────────────────────────────
    ticket_stats = await db.execute(
        text("""
            SELECT
                COUNT(*) as total,
                COUNT(*) FILTER (WHERE status = 'pending') as pending,
                COUNT(*) FILTER (WHERE status = 'classifying') as classifying,
                COUNT(*) FILTER (WHERE status = 'classified') as classified,
                COUNT(*) FILTER (WHERE status = 'fraud_checking') as fraud_checking,
                COUNT(*) FILTER (WHERE status = 'fraud_checked') as fraud_checked,
                COUNT(*) FILTER (WHERE status = 'routed') as routed,
                COUNT(*) FILTER (WHERE status = 'resolved') as resolved,
                COUNT(*) FILTER (WHERE status LIKE '%error%') as errored,
                COUNT(*) FILTER (WHERE created_at >= NOW() - INTERVAL '24 hours') as last_24h,
                COUNT(*) FILTER (WHERE created_at >= NOW() - INTERVAL '1 hour') as last_1h
            FROM tickets
        """)
    )
    ts = ticket_stats.fetchone()

    # ── Classification stats ──────────────────────────────────────
    cls_stats = await db.execute(
        text("""
            SELECT
                COUNT(*) as total_classified,
                COUNT(*) FILTER (WHERE priority = 'critical') as critical_count,
                COUNT(*) FILTER (WHERE priority = 'high') as high_count,
                COUNT(*) FILTER (WHERE priority = 'medium') as medium_count,
                COUNT(*) FILTER (WHERE priority = 'low') as low_count,
                COUNT(*) FILTER (WHERE fraud_score >= :high_threshold) as high_fraud,
                AVG(fraud_score) as avg_fraud_score
            FROM classifications
        """),
        {"high_threshold": settings.fraud_high_risk_threshold},
    )
    cs = cls_stats.fetchone()

    # ── Category breakdown ────────────────────────────────────────
    category_breakdown = await db.execute(
        text("""
            SELECT category, COUNT(*) as count
            FROM classifications
            GROUP BY category
            ORDER BY count DESC
        """)
    )
    categories = category_breakdown.fetchall()

    # ── Team workload ─────────────────────────────────────────────
    team_workload = await db.execute(
        text("""
            SELECT
                assigned_team,
                COUNT(*) as total_assigned,
                COUNT(*) FILTER (WHERE resolved = false) as open_tickets,
                COUNT(*) FILTER (WHERE resolved = true) as resolved_tickets,
                COUNT(*) FILTER (WHERE severity_level = 'critical') as critical_tickets
            FROM routing
            GROUP BY assigned_team
            ORDER BY open_tickets DESC
        """)
    )
    teams = team_workload.fetchall()

    # ── Fraud stats ───────────────────────────────────────────────
    fraud_stats = await db.execute(
        text("""
            SELECT
                COUNT(*) as total_flags,
                COUNT(DISTINCT wallet_address) as flagged_wallets,
                COUNT(*) FILTER (WHERE flag_score >= :high_threshold) as critical_flags,
                COUNT(*) FILTER (WHERE created_at >= NOW() - INTERVAL '24 hours') as flags_24h
            FROM fraud_flags
        """),
        {"high_threshold": settings.fraud_high_risk_threshold},
    )
    fs = fraud_stats.fetchone()

    # ── Recent high-priority incidents ────────────────────────────
    recent_incidents = await db.execute(
        text("""
            SELECT
                t.id, t.user_id, t.wallet_address, t.status, t.created_at,
                c.category, c.priority, c.fraud_score,
                r.assigned_team, r.severity_level
            FROM tickets t
            LEFT JOIN classifications c ON c.ticket_id = t.id
            LEFT JOIN routing r ON r.ticket_id = t.id
            WHERE c.priority IN ('critical', 'high')
               OR c.fraud_score >= :fraud_threshold
            ORDER BY t.created_at DESC
            LIMIT 10
        """),
        {"fraud_threshold": settings.fraud_medium_risk_threshold},
    )
    incidents = recent_incidents.fetchall()

    return {
        "tickets": {
            "total": ts.total or 0,
            "by_status": {
                "pending": ts.pending or 0,
                "processing": (ts.classifying or 0) + (ts.fraud_checking or 0),
                "classified": ts.classified or 0,
                "fraud_checked": ts.fraud_checked or 0,
                "routed": ts.routed or 0,
                "resolved": ts.resolved or 0,
                "errored": ts.errored or 0,
            },
            "last_24h": ts.last_24h or 0,
            "last_1h": ts.last_1h or 0,
        },
        "classifications": {
            "total": cs.total_classified or 0,
            "by_priority": {
                "critical": cs.critical_count or 0,
                "high": cs.high_count or 0,
                "medium": cs.medium_count or 0,
                "low": cs.low_count or 0,
            },
            "high_fraud_count": cs.high_fraud or 0,
            "avg_fraud_score": round(cs.avg_fraud_score or 0, 3),
            "by_category": [
                {"category": r.category, "count": r.count}
                for r in categories
            ],
        },
        "fraud": {
            "total_flags": fs.total_flags or 0,
            "flagged_wallets": fs.flagged_wallets or 0,
            "critical_flags": fs.critical_flags or 0,
            "flags_last_24h": fs.flags_24h or 0,
        },
        "team_workload": [
            {
                "team": r.assigned_team,
                "total_assigned": r.total_assigned,
                "open": r.open_tickets,
                "resolved": r.resolved_tickets,
                "critical": r.critical_tickets,
            }
            for r in teams
        ],
        "recent_high_priority_incidents": [
            {
                "ticket_id": str(i.id),
                "user_id": i.user_id,
                "wallet_address": i.wallet_address,
                "status": i.status,
                "category": i.category,
                "priority": i.priority,
                "fraud_score": i.fraud_score,
                "assigned_team": i.assigned_team,
                "severity_level": i.severity_level,
                "created_at": i.created_at.isoformat(),
            }
            for i in incidents
        ],
    }
