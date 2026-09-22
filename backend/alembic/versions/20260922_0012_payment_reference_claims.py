"""add global payment reference claims

Revision ID: 20260922_0012
Revises: 20260922_0011
Create Date: 2026-09-22
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260922_0012"
down_revision = "20260922_0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "payment_reference_claims",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("method", sa.String(length=40), nullable=False),
        sa.Column("reference", sa.String(length=180), nullable=False),
        sa.Column("source_type", sa.String(length=40), nullable=False),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "method",
            "reference",
            name="uq_payment_reference_method_reference",
        ),
    )
    op.create_index(
        "ix_payment_reference_claims_method",
        "payment_reference_claims",
        ["method"],
        unique=False,
    )
    op.create_index(
        "ix_payment_reference_claims_source_type",
        "payment_reference_claims",
        ["source_type"],
        unique=False,
    )
    op.create_index(
        "ix_payment_reference_claims_source_id",
        "payment_reference_claims",
        ["source_id"],
        unique=False,
    )

    op.execute(
        """
        INSERT INTO payment_reference_claims (id, method, reference, source_type, source_id)
        SELECT gen_random_uuid(), lower(trim(method)), upper(trim(reference)), 'booking', booking_id
        FROM booking_payments
        WHERE method IS NOT NULL AND reference IS NOT NULL
        ON CONFLICT ON CONSTRAINT uq_payment_reference_method_reference DO NOTHING
        """
    )
    op.execute(
        """
        INSERT INTO payment_reference_claims (id, method, reference, source_type, source_id)
        SELECT gen_random_uuid(), lower(trim(payment_method)), upper(trim(payment_reference)), 'advert_charge', id
        FROM advert_charges
        WHERE payment_method IS NOT NULL AND payment_reference IS NOT NULL
        ON CONFLICT ON CONSTRAINT uq_payment_reference_method_reference DO NOTHING
        """
    )


def downgrade() -> None:
    op.drop_index("ix_payment_reference_claims_source_id", table_name="payment_reference_claims")
    op.drop_index("ix_payment_reference_claims_source_type", table_name="payment_reference_claims")
    op.drop_index("ix_payment_reference_claims_method", table_name="payment_reference_claims")
    op.drop_table("payment_reference_claims")
