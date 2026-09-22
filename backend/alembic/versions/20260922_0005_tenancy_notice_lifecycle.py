"""add tenancy and notice lifecycle

Revision ID: 20260922_0005
Revises: 20260922_0004
Create Date: 2026-09-22
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260922_0005"
down_revision = "20260922_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tenancies",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("booking_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("bookings.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("unit_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("units.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("status", sa.String(40), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("notice_given_at", sa.DateTime(timezone=True)),
        sa.Column("expected_move_out", sa.Date()),
        sa.Column("allow_readvertise", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("ended_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("booking_id", name="uq_tenancies_booking_id"),
    )
    op.create_index("ix_tenancies_booking_id", "tenancies", ["booking_id"])
    op.create_index("ix_tenancies_unit_id", "tenancies", ["unit_id"])
    op.create_index("ix_tenancies_tenant_id", "tenancies", ["tenant_id"])
    op.create_index("ix_tenancies_status", "tenancies", ["status"])
    op.create_index(
        "uq_tenancies_live_unit",
        "tenancies",
        ["unit_id"],
        unique=True,
        postgresql_where=sa.text("status IN ('active', 'notice_given')"),
    )


def downgrade() -> None:
    op.drop_index("uq_tenancies_live_unit", table_name="tenancies")
    op.drop_index("ix_tenancies_status", table_name="tenancies")
    op.drop_index("ix_tenancies_tenant_id", table_name="tenancies")
    op.drop_index("ix_tenancies_unit_id", table_name="tenancies")
    op.drop_index("ix_tenancies_booking_id", table_name="tenancies")
    op.drop_table("tenancies")
