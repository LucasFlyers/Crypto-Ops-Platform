"""
app/models/fraud.py
─────────────────────
Fraud flag records.
A wallet can accumulate multiple flags of different types.
The aggregate score is computed at query time by the fraud engine.

flag_type values:
  - repeated_complaints    : multiple tickets from same wallet
  - high_tx_failure_rate   : many failed transactions
  - multi_account_wallet   : multiple users referencing same wallet
  - linked_flagged_wallet  : associated with known bad wallet
  - ai_high_fraud_score    : AI classifier returned fraud_score > threshold
"""

import uuid
from datetime import datetime

from sqlalchemy import String, Float, DateTime, Index, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class FraudFlag(Base):
    __tablename__ = "fraud_flags"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    wallet_address: Mapped[str] = mapped_column(
        String(256),
        nullable=False,
        index=True,
    )
    flag_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    flag_score: Mapped[float] = mapped_column(Float, nullable=False)
    evidence: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    __table_args__ = (
        # Fraud engine: all flags for a wallet sorted by time
        Index("ix_fraud_flags_wallet_created", "wallet_address", "created_at"),
        # Dashboard: recent high-score flags
        Index("ix_fraud_flags_score_created", "flag_score", "created_at"),
    )

    def __repr__(self) -> str:
        return (
            f"<FraudFlag wallet={self.wallet_address[:12]}... "
            f"type={self.flag_type} score={self.flag_score:.2f}>"
        )
