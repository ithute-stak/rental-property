"""add viewing reminder delivery state

Revision ID: 20260922_0010
Revises: 20260922_0009
Create Date: 2026-09-22
"""

from alembic import op
import sqlalchemy as sa

revision = "20260922_0010"
down_revision = "20260922_0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "viewing_requests",
        sa.Column("reminder_sent_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_viewing_requests_reminder_due",
        "viewing_requests",
        ["status", "scheduled_at", "reminder_sent_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_viewing_requests_reminder_due", table_name="viewing_requests")
    op.drop_column("viewing_requests", "reminder_sent_at")
