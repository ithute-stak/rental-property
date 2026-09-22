"""add persistent bookings payments ledger and notifications

Revision ID: 20260922_0004
Revises: 20260922_0003
Create Date: 2026-09-22
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260922_0004"
down_revision = "20260922_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "bookings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("unit_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("units.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("seeker_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("status", sa.String(40), nullable=False),
        sa.Column("move_in_date", sa.Date(), nullable=False),
        sa.Column("amount_due", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="LSL"),
        sa.Column("payment_due_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("confirmed_at", sa.DateTime(timezone=True)),
        sa.Column("cancelled_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_bookings_unit_id", "bookings", ["unit_id"])
    op.create_index("ix_bookings_seeker_id", "bookings", ["seeker_id"])
    op.create_index("ix_bookings_status", "bookings", ["status"])
    op.create_index(
        "uq_bookings_active_unit",
        "bookings",
        ["unit_id"],
        unique=True,
        postgresql_where=sa.text("status IN ('pending_payment', 'payment_review', 'confirmed')"),
    )

    op.create_table(
        "booking_status_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("booking_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("bookings.id", ondelete="CASCADE"), nullable=False),
        sa.Column("from_status", sa.String(40)),
        sa.Column("to_status", sa.String(40), nullable=False),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("note", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_booking_status_history_booking_id", "booking_status_history", ["booking_id"])

    op.create_table(
        "booking_payments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("booking_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("bookings.id", ondelete="CASCADE"), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="LSL"),
        sa.Column("status", sa.String(40), nullable=False),
        sa.Column("method", sa.String(40)),
        sa.Column("reference", sa.String(180)),
        sa.Column("submitted_at", sa.DateTime(timezone=True)),
        sa.Column("confirmed_at", sa.DateTime(timezone=True)),
        sa.Column("confirmed_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("booking_id", name="uq_booking_payments_booking_id"),
    )
    op.create_index("ix_booking_payments_booking_id", "booking_payments", ["booking_id"])
    op.create_index("ix_booking_payments_status", "booking_payments", ["status"])

    op.create_table(
        "ledger_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("booking_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("bookings.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("payment_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("booking_payments.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("account", sa.String(80), nullable=False),
        sa.Column("direction", sa.String(10), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="LSL"),
        sa.Column("memo", sa.String(240), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_ledger_entries_booking_id", "ledger_entries", ["booking_id"])
    op.create_index("ix_ledger_entries_payment_id", "ledger_entries", ["payment_id"])
    op.create_index("ix_ledger_entries_account", "ledger_entries", ["account"])

    op.create_table(
        "notifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("notification_type", sa.String(60), nullable=False),
        sa.Column("title", sa.String(180), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("read_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_notifications_user_id", "notifications", ["user_id"])
    op.create_index("ix_notifications_notification_type", "notifications", ["notification_type"])
    op.create_index("ix_notifications_created_at", "notifications", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_notifications_created_at", table_name="notifications")
    op.drop_index("ix_notifications_notification_type", table_name="notifications")
    op.drop_index("ix_notifications_user_id", table_name="notifications")
    op.drop_table("notifications")

    op.drop_index("ix_ledger_entries_account", table_name="ledger_entries")
    op.drop_index("ix_ledger_entries_payment_id", table_name="ledger_entries")
    op.drop_index("ix_ledger_entries_booking_id", table_name="ledger_entries")
    op.drop_table("ledger_entries")

    op.drop_index("ix_booking_payments_status", table_name="booking_payments")
    op.drop_index("ix_booking_payments_booking_id", table_name="booking_payments")
    op.drop_table("booking_payments")

    op.drop_index("ix_booking_status_history_booking_id", table_name="booking_status_history")
    op.drop_table("booking_status_history")

    op.drop_index("uq_bookings_active_unit", table_name="bookings")
    op.drop_index("ix_bookings_status", table_name="bookings")
    op.drop_index("ix_bookings_seeker_id", table_name="bookings")
    op.drop_index("ix_bookings_unit_id", table_name="bookings")
    op.drop_table("bookings")
