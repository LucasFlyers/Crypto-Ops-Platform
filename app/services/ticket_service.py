"""
app/services/ticket_service.py
────────────────────────────────
Ticket business logic layer.
Sits between the API layer and the database/workers.
Keeps route handlers thin and testable.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import text, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.ticket import Ticket
from app.schemas.ticket import TicketCreateRequest
from app.utils.logging import get_logger

logger = get_logger(__name__)


class DuplicateTicketError(Exception):
    """Raised when a ticket with the same transaction_id already exists."""
    def __init__(self, transaction_id: str, existing_ticket_id: uuid.UUID):
        self.transaction_id = transaction_id
        self.existing_ticket_id = existing_ticket_id
        super().__init__(f"Ticket already exists for transaction {transaction_id}")


class TicketService:
    """Handles ticket creation, retrieval, and status management."""

    async def create_ticket(
        self,
        session: AsyncSession,
        request: TicketCreateRequest,
    ) -> Ticket:
        """
        Create and persist a new ticket.
        Checks idempotency via transaction_id before inserting.

        Args:
            session: Async database session
            request: Validated ticket creation request

        Returns:
            Created Ticket ORM instance

        Raises:
            DuplicateTicketError: If transaction_id already exists
        """
        # ── Idempotency check ─────────────────────────────────────
        if request.transaction_id:
            existing = await session.execute(
                text("SELECT id FROM tickets WHERE transaction_id = :tx_id"),
                {"tx_id": request.transaction_id},
            )
            row = existing.fetchone()
            if row:
                logger.warning(
                    "duplicate_ticket_rejected",
                    transaction_id=request.transaction_id,
                    existing_id=str(row.id),
                )
                raise DuplicateTicketError(
                    transaction_id=request.transaction_id,
                    existing_ticket_id=row.id,
                )

        # ── Create ticket ─────────────────────────────────────────
        ticket = Ticket(
            user_id=request.user_id,
            wallet_address=request.wallet_address,
            transaction_id=request.transaction_id,
            message=request.message,
            status="pending",
        )
        session.add(ticket)
        await session.flush()  # Get ID without committing
        await session.commit()
        await session.refresh(ticket)

        logger.info(
            "ticket_created",
            ticket_id=str(ticket.id),
            user_id=ticket.user_id,
            has_wallet=bool(ticket.wallet_address),
            has_transaction=bool(ticket.transaction_id),
        )

        return ticket

    async def get_ticket(
        self,
        session: AsyncSession,
        ticket_id: uuid.UUID,
    ) -> Ticket | None:
        """
        Fetch a ticket with its classification and routing eagerly loaded.
        """
        result = await session.execute(
            select(Ticket)
            .where(Ticket.id == ticket_id)
            .options(
                selectinload(Ticket.classification),
                selectinload(Ticket.routing),
            )
        )
        return result.scalar_one_or_none()

    async def dispatch_classification(self, ticket_id: uuid.UUID) -> None:
        """
        Enqueue the classification task for async processing.
        This is called after ticket creation.
        """
        from app.workers.tasks import classify_ticket_task
        classify_ticket_task.apply_async(
            args=[str(ticket_id)],
            countdown=0,  # Process immediately
        )
        logger.info(
            "classification_task_dispatched",
            ticket_id=str(ticket_id),
        )


def get_ticket_service() -> TicketService:
    """Dependency injection factory for TicketService."""
    return TicketService()
