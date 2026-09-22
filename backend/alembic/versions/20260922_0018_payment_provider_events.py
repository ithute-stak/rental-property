"""Add durable payment-provider webhook events.

Revision ID: 20260922_0018
Revises: 20260922_0017
Create Date: 2026-09-22
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260922_0018"
down_revision: str | None = "20260922_0017"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "payment_provider_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider", sa.String(length=60), nullable=False),
        sa.Column("event_id", sa.String(length=180), nullable=False),
        sa.Column("event_type", sa.String(length=80), nullable=False),
        sa.Column("provider_transaction_id", sa.String(length=180), nullable=True),
        sa.Column("source_type", sa.String(length=40), nullable=False),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("outcome", sa.String(length=30), nullable=False),
        sa.Column("amount", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("currency", sa.String(length=3), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("payload_sha256", sa.String(length=64), nullable=False),
        sa.Column("processing_status", sa.String(length=40), nullable=False),
        sa.Column("processing_message", sa.Text(), nullable=True),
        sa.Column(
            "received_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider", "event_id", name="uq_payment_provider_event"),
    )
    op.create_index("ix_payment_provider_events_provider", "payment_provider_events", ["provider"])
    op.create_index(
        "ix_payment_provider_events_provider_transaction_id",
        "payment_provider_events",
        ["provider_transaction_id"],
    )
    op.create_index(
        "ix_payment_provider_events_source_type", "payment_provider_events", ["source_type"]
    )
    op.create_index(
        "ix_payment_provider_events_source_id", "payment_provider_events", ["source_id"]
    )
    op.create_index("ix_payment_provider_events_outcome", "payment_provider_events", ["outcome"])
    op.create_index(
        "ix_payment_provider_events_processing_status",
        "payment_provider_events",
        ["processing_status"],
    )
    op.create_index(
        "ix_payment_provider_events_received_at", "payment_provider_events", ["received_at"]
    )


def downgrade() -> None:
    op.drop_index("ix_payment_provider_events_received_at", table_name="payment_provider_events")
    op.drop_index(
        "ix_payment_provider_events_processing_status", table_name="payment_provider_events"
    )
    op.drop_index("ix_payment_provider_events_outcome", table_name="payment_provider_events")
    op.drop_index("ix_payment_provider_events_source_id", table_name="payment_provider_events")
    op.drop_index("ix_payment_provider_events_source_type", table_name="payment_provider_events")
    op.drop_index(
        "ix_payment_provider_events_provider_transaction_id", table_name="payment_provider_events"
    )
    op.drop_index("ix_payment_provider_events_provider", table_name="payment_provider_events")
    op.drop_table("payment_provider_events")
