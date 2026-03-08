"""
app/models/ticket.py
─────────────────────
Ticket ORM model — the core entity of the system.

Status flow:
  pending → classified → fraud_checked → routed → resolved
"""

import uuid
from datetime import datetime

from sqlalchemy import String, Text, DateTime, Index, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class Ticket(Base):
    __tablename__ = "tickets"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    wallet_address: Mapped[str | None] = mapped_column(String(256), nullable=True, index=True)
    transaction_id: Mapped[str | None] = mapped_column(String(256), nullable=True, unique=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="pending",
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    classification: Mapped["Classification"] = relationship(  # noqa: F821
        back_populates="ticket",
        uselist=False,
        lazy="select",
    )
    routing: Mapped["Routing"] = relationship(  # noqa: F821
        back_populates="ticket",
        uselist=False,
        lazy="select",
    )

    # Composite indexes for common query patterns
    __table_args__ = (
        # Dashboard: tickets by status + created_at (sorted list)
        Index("ix_tickets_status_created", "status", "created_at"),
        # Fraud engine: all tickets for a wallet in time window
        Index("ix_tickets_wallet_created", "wallet_address", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<Ticket id={self.id} user={self.user_id} status={self.status}>"
