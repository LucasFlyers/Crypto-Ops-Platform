"""
app/models/classification.py
──────────────────────────────
AI classification result linked to a ticket.
One-to-one relationship: each ticket gets one classification.
"""

import uuid
from datetime import datetime

from sqlalchemy import String, Text, Float, DateTime, ForeignKey, Index, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class Classification(Base):
    __tablename__ = "classifications"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    ticket_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tickets.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,  # One classification per ticket
        index=True,
    )
    category: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    priority: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    fraud_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    ai_reasoning: Mapped[str] = mapped_column(Text, nullable=False)
    ai_model_used: Mapped[str] = mapped_column(String(128), nullable=False)
    processed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # Relationship back to ticket
    ticket: Mapped["Ticket"] = relationship(  # noqa: F821
        back_populates="classification",
    )

    __table_args__ = (
        # Dashboard: high fraud score tickets
        Index("ix_classifications_fraud_score", "fraud_score"),
        # Filter by category + priority
        Index("ix_classifications_category_priority", "category", "priority"),
    )

    def __repr__(self) -> str:
        return (
            f"<Classification ticket={self.ticket_id} "
            f"category={self.category} priority={self.priority} "
            f"fraud_score={self.fraud_score:.2f}>"
        )
