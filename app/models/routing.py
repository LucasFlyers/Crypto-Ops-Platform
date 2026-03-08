"""
app/models/routing.py
──────────────────────
Routing decision record.
Documents exactly which team was assigned, why, and when.
The `rule_matched` field creates the audit trail regulators require.

assigned_team values:
  - compliance_team
  - security_team
  - customer_support
  - technical_operations
  - fraud_investigation
"""

import uuid
from datetime import datetime

from sqlalchemy import String, Boolean, DateTime, ForeignKey, Index, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class Routing(Base):
    __tablename__ = "routing"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    ticket_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tickets.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,  # One routing decision per ticket
        index=True,
    )
    assigned_team: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    severity_level: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    rule_matched: Mapped[str] = mapped_column(String(128), nullable=False)
    resolved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # Relationship back to ticket
    ticket: Mapped["Ticket"] = relationship(  # noqa: F821
        back_populates="routing",
    )

    __table_args__ = (
        # Dashboard: team workload (open tickets per team)
        Index("ix_routing_team_resolved", "assigned_team", "resolved"),
        # Dashboard: severity breakdown
        Index("ix_routing_severity_resolved", "severity_level", "resolved"),
    )

    def __repr__(self) -> str:
        return (
            f"<Routing ticket={self.ticket_id} "
            f"team={self.assigned_team} severity={self.severity_level} "
            f"resolved={self.resolved}>"
        )
