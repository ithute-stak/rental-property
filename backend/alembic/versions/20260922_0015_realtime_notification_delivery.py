"""add realtime notification delivery state

Revision ID: 20260922_0015
Revises: 20260922_0014
Create Date: 2026-09-22
"""

from alembic import op
import sqlalchemy as sa

revision = "20260922_0015"
down_revision = "20260922_0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "notifications",
        sa.Column("realtime_published_at", sa.DateTime(timezone=True), nullable=True),
    )

    # Notifications that predate realtime delivery are historical inbox rows,
    # not new realtime events. Mark them as already handled so deployment does
    # not replay the entire notification history to currently connected users.
    op.execute(
        """
        UPDATE notifications
        SET realtime_published_at = created_at
        WHERE realtime_published_at IS NULL
        """
    )

    op.create_index(
        "ix_notifications_realtime_pending",
        "notifications",
        ["created_at"],
        unique=False,
        postgresql_where=sa.text("realtime_published_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("ix_notifications_realtime_pending", table_name="notifications")
    op.drop_column("notifications", "realtime_published_at")
