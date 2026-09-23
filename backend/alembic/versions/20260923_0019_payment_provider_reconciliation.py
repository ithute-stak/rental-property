"""Add payment-provider reconciliation metadata.

Revision ID: 20260923_0019
Revises: 20260922_0018
Create Date: 2026-09-23
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260923_0019"
down_revision: str | None = "20260922_0018"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "payment_provider_events",
        sa.Column("reconciled_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "payment_provider_events",
        sa.Column("reconciled_by", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "payment_provider_events",
        sa.Column("resolution_note", sa.Text(), nullable=True),
    )
    op.create_foreign_key(
        "fk_payment_provider_events_reconciled_by_users",
        "payment_provider_events",
        "users",
        ["reconciled_by"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_payment_provider_events_reconciled_by",
        "payment_provider_events",
        ["reconciled_by"],
    )
    op.create_index(
        "ix_payment_provider_events_reconciled_at",
        "payment_provider_events",
        ["reconciled_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_payment_provider_events_reconciled_at", table_name="payment_provider_events")
    op.drop_index("ix_payment_provider_events_reconciled_by", table_name="payment_provider_events")
    op.drop_constraint(
        "fk_payment_provider_events_reconciled_by_users",
        "payment_provider_events",
        type_="foreignkey",
    )
    op.drop_column("payment_provider_events", "resolution_note")
    op.drop_column("payment_provider_events", "reconciled_by")
    op.drop_column("payment_provider_events", "reconciled_at")
