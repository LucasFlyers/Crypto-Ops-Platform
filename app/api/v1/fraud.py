"""
app/api/v1/fraud.py
────────────────────
Fraud monitoring API endpoints.

GET /api/v1/fraud/flags              - List all fraud flags (recent first)
GET /api/v1/fraud/wallet/{address}   - Full fraud profile for a wallet
GET /api/v1/fraud/summary            - Aggregate fraud statistics
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.config import settings
from app.utils.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/fraud", tags=["Fraud Detection"])


@router.get(
    "/flags",
    summary="List recent fraud flags",
)
async def list_fraud_flags(
    min_score: float = Query(default=0.0, ge=0.0, le=1.0),
    flag_type: Optional[str] = Query(default=None),
    limit: int = Query(default=50, le=200, ge=1),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """List fraud flags, optionally filtered by minimum score or flag type."""
    query = """
        SELECT wallet_address, flag_type, flag_score, evidence, created_at
        FROM fraud_flags
        WHERE flag_score >= :min_score
    """
    params: dict = {"min_score": min_score}

    if flag_type:
        query += " AND flag_type = :flag_type"
        params["flag_type"] = flag_type

    query += " ORDER BY created_at DESC LIMIT :limit"
    params["limit"] = limit

    result = await db.execute(text(query), params)
    rows = result.fetchall()

    return {
        "total": len(rows),
        "flags": [
            {
                "wallet_address": r.wallet_address,
                "flag_type": r.flag_type,
                "flag_score": r.flag_score,
                "evidence": r.evidence,
                "created_at": r.created_at.isoformat(),
            }
            for r in rows
        ],
    }


@router.get(
    "/wallet/{wallet_address}",
    summary="Get fraud profile for a specific wallet",
)
async def get_wallet_fraud_profile(
    wallet_address: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Full fraud intelligence report for a wallet.
    Includes: all flags, ticket history, aggregate risk score.
    """
    # Wallet flags
    flags_result = await db.execute(
        text("""
            SELECT flag_type, flag_score, evidence, created_at
            FROM fraud_flags
            WHERE wallet_address = :wallet
            ORDER BY created_at DESC
        """),
        {"wallet": wallet_address},
    )
    flags = flags_result.fetchall()

    # Ticket history for this wallet
    tickets_result = await db.execute(
        text("""
            SELECT t.id, t.user_id, t.status, t.created_at,
                   c.category, c.priority, c.fraud_score
            FROM tickets t
            LEFT JOIN classifications c ON c.ticket_id = t.id
            WHERE t.wallet_address = :wallet
            ORDER BY t.created_at DESC
            LIMIT 20
        """),
        {"wallet": wallet_address},
    )
    tickets = tickets_result.fetchall()

    # Compute aggregate risk score
    max_flag_score = max((f.flag_score for f in flags), default=0.0)
    flag_count = len(flags)
    unique_flag_types = len(set(f.flag_type for f in flags))
    unique_users = len(set(t.user_id for t in tickets))

    # Determine risk tier
    if max_flag_score >= settings.fraud_high_risk_threshold:
        risk_tier = "critical" if flag_count >= 3 else "high"
    elif max_flag_score >= settings.fraud_medium_risk_threshold:
        risk_tier = "medium"
    elif max_flag_score > 0:
        risk_tier = "low"
    else:
        risk_tier = "clean"

    return {
        "wallet_address": wallet_address,
        "risk_tier": risk_tier,
        "max_flag_score": round(max_flag_score, 3),
        "total_flags": flag_count,
        "unique_flag_types": unique_flag_types,
        "unique_user_count": unique_users,
        "total_tickets": len(tickets),
        "flags": [
            {
                "flag_type": f.flag_type,
                "flag_score": f.flag_score,
                "evidence": f.evidence,
                "created_at": f.created_at.isoformat(),
            }
            for f in flags
        ],
        "recent_tickets": [
            {
                "ticket_id": str(t.id),
                "user_id": t.user_id,
                "status": t.status,
                "category": t.category,
                "priority": t.priority,
                "fraud_score": t.fraud_score,
                "created_at": t.created_at.isoformat(),
            }
            for t in tickets
        ],
    }


@router.get(
    "/summary",
    summary="Aggregate fraud statistics",
)
async def fraud_summary(db: AsyncSession = Depends(get_db)) -> dict:
    """Dashboard-friendly fraud statistics summary."""
    stats = await db.execute(
        text("""
            SELECT
                COUNT(*) as total_flags,
                COUNT(DISTINCT wallet_address) as flagged_wallets,
                AVG(flag_score) as avg_flag_score,
                COUNT(*) FILTER (WHERE flag_score >= :high_threshold) as high_risk_flags,
                COUNT(*) FILTER (WHERE created_at >= NOW() - INTERVAL '24 hours') as flags_last_24h
            FROM fraud_flags
        """),
        {"high_threshold": settings.fraud_high_risk_threshold},
    )
    row = stats.fetchone()

    by_type = await db.execute(
        text("""
            SELECT flag_type, COUNT(*) as count, AVG(flag_score) as avg_score
            FROM fraud_flags
            GROUP BY flag_type
            ORDER BY count DESC
        """)
    )
    type_rows = by_type.fetchall()

    return {
        "total_flags": row.total_flags or 0,
        "flagged_wallets": row.flagged_wallets or 0,
        "avg_flag_score": round(row.avg_flag_score or 0, 3),
        "high_risk_flags": row.high_risk_flags or 0,
        "flags_last_24h": row.flags_last_24h or 0,
        "by_flag_type": [
            {
                "flag_type": r.flag_type,
                "count": r.count,
                "avg_score": round(r.avg_score, 3),
            }
            for r in type_rows
        ],
    }
