"""Initial schema - tickets, classifications, fraud_flags, routing

Revision ID: 001_initial_schema
Revises:
Create Date: 2026-03-06 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── tickets ──────────────────────────────────────────────────
    op.create_table(
        "tickets",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.String(128), nullable=False),
        sa.Column("wallet_address", sa.String(256), nullable=True),
        sa.Column("transaction_id", sa.String(256), nullable=True),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("transaction_id"),
    )
    op.create_index("ix_tickets_user_id", "tickets", ["user_id"])
    op.create_index("ix_tickets_wallet_address", "tickets", ["wallet_address"])
    op.create_index("ix_tickets_status", "tickets", ["status"])
    op.create_index("ix_tickets_created_at", "tickets", ["created_at"])
    op.create_index(
        "ix_tickets_status_created", "tickets", ["status", "created_at"]
    )
    op.create_index(
        "ix_tickets_wallet_created", "tickets", ["wallet_address", "created_at"]
    )

    # ── classifications ───────────────────────────────────────────
    op.create_table(
        "classifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ticket_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("category", sa.String(64), nullable=False),
        sa.Column("priority", sa.String(16), nullable=False),
        sa.Column("fraud_score", sa.Float(), nullable=False),
        sa.Column("ai_reasoning", sa.Text(), nullable=False),
        sa.Column("ai_model_used", sa.String(128), nullable=False),
        sa.Column(
            "processed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["ticket_id"], ["tickets.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("ticket_id"),
    )
    op.create_index("ix_classifications_ticket_id", "classifications", ["ticket_id"])
    op.create_index("ix_classifications_category", "classifications", ["category"])
    op.create_index("ix_classifications_priority", "classifications", ["priority"])
    op.create_index(
        "ix_classifications_fraud_score", "classifications", ["fraud_score"]
    )
    op.create_index(
        "ix_classifications_category_priority",
        "classifications",
        ["category", "priority"],
    )

    # ── fraud_flags ───────────────────────────────────────────────
    op.create_table(
        "fraud_flags",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("wallet_address", sa.String(256), nullable=False),
        sa.Column("flag_type", sa.String(64), nullable=False),
        sa.Column("flag_score", sa.Float(), nullable=False),
        sa.Column("evidence", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_fraud_flags_wallet_address", "fraud_flags", ["wallet_address"])
    op.create_index("ix_fraud_flags_flag_type", "fraud_flags", ["flag_type"])
    op.create_index(
        "ix_fraud_flags_wallet_created",
        "fraud_flags",
        ["wallet_address", "created_at"],
    )
    op.create_index(
        "ix_fraud_flags_score_created",
        "fraud_flags",
        ["flag_score", "created_at"],
    )

    # ── routing ───────────────────────────────────────────────────
    op.create_table(
        "routing",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ticket_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("assigned_team", sa.String(64), nullable=False),
        sa.Column("severity_level", sa.String(16), nullable=False),
        sa.Column("rule_matched", sa.String(128), nullable=False),
        sa.Column("resolved", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["ticket_id"], ["tickets.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("ticket_id"),
    )
    op.create_index("ix_routing_ticket_id", "routing", ["ticket_id"])
    op.create_index("ix_routing_assigned_team", "routing", ["assigned_team"])
    op.create_index("ix_routing_severity_level", "routing", ["severity_level"])
    op.create_index(
        "ix_routing_team_resolved", "routing", ["assigned_team", "resolved"]
    )
    op.create_index(
        "ix_routing_severity_resolved", "routing", ["severity_level", "resolved"]
    )


def downgrade() -> None:
    op.drop_table("routing")
    op.drop_table("fraud_flags")
    op.drop_table("classifications")
    op.drop_table("tickets")
