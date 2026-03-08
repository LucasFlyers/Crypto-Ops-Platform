"""
app/api/v1/tickets.py
──────────────────────
Ticket API endpoints.

POST /api/v1/tickets         - Ingest new ticket
GET  /api/v1/tickets/{id}    - Get ticket details
GET  /api/v1/tickets         - List tickets with filtering
PATCH /api/v1/tickets/{id}/resolve - Mark ticket as resolved
"""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import text, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.ticket import (
    TicketCreateRequest,
    TicketResponse,
    TicketDetailResponse,
)
from app.services.ticket_service import TicketService, DuplicateTicketError, get_ticket_service
from app.utils.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/tickets", tags=["Tickets"])


@router.post(
    "",
    response_model=TicketResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Ingest a new operational ticket",
    description=(
        "Accepts an operational event (withdrawal complaint, wallet issue, etc.), "
        "stores it, and asynchronously triggers AI classification + fraud analysis."
    ),
)
async def create_ticket(
    request: TicketCreateRequest,
    db: AsyncSession = Depends(get_db),
    ticket_service: TicketService = Depends(get_ticket_service),
) -> TicketResponse:
    """
    Ticket ingestion endpoint.
    Returns 202 Accepted — processing happens asynchronously.
    """
    try:
        ticket = await ticket_service.create_ticket(session=db, request=request)
        await ticket_service.dispatch_classification(ticket_id=ticket.id)

        logger.info(
            "ticket_ingested",
            ticket_id=str(ticket.id),
            user_id=ticket.user_id,
        )

        return TicketResponse(
            ticket_id=ticket.id,
            status="pending",
            message="Ticket received and queued for processing",
        )

    except DuplicateTicketError as e:
        logger.warning(
            "duplicate_ticket_request",
            transaction_id=e.transaction_id,
        )
        # Return 200 with existing ticket ID (idempotent behavior)
        return TicketResponse(
            ticket_id=e.existing_ticket_id,
            status="already_exists",
            message=f"Ticket already exists for transaction {e.transaction_id}",
        )


@router.get(
    "/{ticket_id}",
    response_model=TicketDetailResponse,
    summary="Get full ticket details",
)
async def get_ticket(
    ticket_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    ticket_service: TicketService = Depends(get_ticket_service),
) -> TicketDetailResponse:
    """Retrieve a ticket with its classification and routing information."""
    ticket = await ticket_service.get_ticket(session=db, ticket_id=ticket_id)

    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ticket {ticket_id} not found",
        )

    return TicketDetailResponse.model_validate(ticket)


@router.get(
    "",
    summary="List tickets with optional filtering",
)
async def list_tickets(
    status_filter: Optional[str] = Query(default=None, alias="status"),
    limit: int = Query(default=50, le=200, ge=1),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """List tickets with optional status filtering and pagination."""
    query = "SELECT id, user_id, wallet_address, transaction_id, status, created_at FROM tickets"
    params: dict = {}

    if status_filter:
        query += " WHERE status = :status"
        params["status"] = status_filter

    query += " ORDER BY created_at DESC LIMIT :limit OFFSET :offset"
    params["limit"] = limit
    params["offset"] = offset

    result = await db.execute(text(query), params)
    rows = result.fetchall()

    count_query = "SELECT COUNT(*) FROM tickets"
    if status_filter:
        count_query += " WHERE status = :status"
    count_result = await db.execute(
        text(count_query),
        {"status": status_filter} if status_filter else {},
    )
    total = count_result.scalar()

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "tickets": [
            {
                "id": str(r.id),
                "user_id": r.user_id,
                "wallet_address": r.wallet_address,
                "transaction_id": r.transaction_id,
                "status": r.status,
                "created_at": r.created_at.isoformat(),
            }
            for r in rows
        ],
    }


@router.patch(
    "/{ticket_id}/resolve",
    summary="Mark a ticket as resolved",
)
async def resolve_ticket(
    ticket_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Mark a ticket and its routing record as resolved."""
    # Check ticket exists
    ticket_row = await db.execute(
        text("SELECT id, status FROM tickets WHERE id = :id"),
        {"id": str(ticket_id)},
    )
    ticket = ticket_row.fetchone()

    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ticket {ticket_id} not found",
        )

    # Update ticket status
    await db.execute(
        text("UPDATE tickets SET status = 'resolved', updated_at = NOW() WHERE id = :id"),
        {"id": str(ticket_id)},
    )

    # Update routing record
    await db.execute(
        text("""
            UPDATE routing
            SET resolved = true, resolved_at = NOW()
            WHERE ticket_id = :id
        """),
        {"id": str(ticket_id)},
    )

    await db.commit()

    logger.info("ticket_resolved", ticket_id=str(ticket_id))

    return {"ticket_id": str(ticket_id), "status": "resolved"}
