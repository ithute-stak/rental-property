"""add advert charges

Revision ID: 20260922_0006
Revises: 20260922_0005
Create Date: 2026-09-22
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260922_0006"
down_revision = "20260922_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "advert_charges",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "property_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("properties.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="LSL"),
        sa.Column("status", sa.String(40), nullable=False),
        sa.Column("note", sa.Text()),
        sa.Column(
            "quoted_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("payment_method", sa.String(40)),
        sa.Column("payment_reference", sa.String(180)),
        sa.Column("payment_submitted_at", sa.DateTime(timezone=True)),
        sa.Column(
            "confirmed_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
        ),
        sa.Column("confirmed_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("property_id", name="uq_advert_charges_property_id"),
        sa.CheckConstraint("amount >= 0", name="ck_advert_charges_amount_nonnegative"),
    )
    op.create_index("ix_advert_charges_property_id", "advert_charges", ["property_id"])
    op.create_index("ix_advert_charges_status", "advert_charges", ["status"])


def downgrade() -> None:
    op.drop_index("ix_advert_charges_status", table_name="advert_charges")
    op.drop_index("ix_advert_charges_property_id", table_name="advert_charges")
    op.drop_table("advert_charges")
