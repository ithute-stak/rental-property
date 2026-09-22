"""add authentication and landlord verification

Revision ID: 20260922_0002
Revises: 20260922_0001
Create Date: 2026-09-22
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260922_0002"
down_revision = "20260922_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("hashed_password", sa.String(255), nullable=True))
    op.execute("UPDATE users SET hashed_password = '' WHERE hashed_password IS NULL")
    op.alter_column("users", "hashed_password", nullable=False)

    op.create_table(
        "landlord_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("business_name", sa.String(180), nullable=True),
        sa.Column("physical_address", sa.String(500), nullable=True),
        sa.Column(
            "verification_status",
            sa.String(32),
            nullable=False,
            server_default="not_submitted",
        ),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_landlord_profiles_user_id",
        "landlord_profiles",
        ["user_id"],
        unique=True,
    )
    op.create_index(
        "ix_landlord_profiles_verification_status",
        "landlord_profiles",
        ["verification_status"],
    )


def downgrade() -> None:
    op.drop_index("ix_landlord_profiles_verification_status", table_name="landlord_profiles")
    op.drop_index("ix_landlord_profiles_user_id", table_name="landlord_profiles")
    op.drop_table("landlord_profiles")
    op.drop_column("users", "hashed_password")
