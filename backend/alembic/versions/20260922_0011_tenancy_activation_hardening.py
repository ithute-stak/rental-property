"""close booking lifecycle at tenancy activation and track inspections

Revision ID: 20260922_0011
Revises: 20260922_0010
Create Date: 2026-09-22
"""

from alembic import op
import sqlalchemy as sa

revision = "20260922_0011"
down_revision = "20260922_0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "tenancies",
        sa.Column("inspection_completed_at", sa.DateTime(timezone=True), nullable=True),
    )

    # A confirmed booking is only an active reservation until it is converted
    # into a tenancy. Existing tenancy rows from earlier revisions therefore
    # need their booking moved out of the partial unique active-booking index.
    op.execute(
        """
        UPDATE bookings
        SET status = 'fulfilled'
        WHERE status = 'confirmed'
          AND id IN (SELECT booking_id FROM tenancies)
        """
    )


def downgrade() -> None:
    op.execute(
        """
        UPDATE bookings
        SET status = 'confirmed'
        WHERE status = 'fulfilled'
          AND id IN (SELECT booking_id FROM tenancies)
        """
    )
    op.drop_column("tenancies", "inspection_completed_at")
