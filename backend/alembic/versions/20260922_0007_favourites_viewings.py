"""add favourites and viewing requests

Revision ID: 20260922_0007
Revises: 20260922_0006
Create Date: 2026-09-22
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260922_0007"
down_revision = "20260922_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "favourite_properties",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "property_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("properties.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("user_id", "property_id", name="uq_favourite_user_property"),
    )
    op.create_index("ix_favourite_properties_user_id", "favourite_properties", ["user_id"])
    op.create_index("ix_favourite_properties_property_id", "favourite_properties", ["property_id"])

    op.create_table(
        "viewing_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "property_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("properties.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "requester_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("status", sa.String(40), nullable=False, server_default="pending"),
        sa.Column("preferred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("response_note", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_viewing_requests_property_id", "viewing_requests", ["property_id"])
    op.create_index("ix_viewing_requests_requester_id", "viewing_requests", ["requester_id"])
    op.create_index("ix_viewing_requests_status", "viewing_requests", ["status"])


def downgrade() -> None:
    op.drop_index("ix_viewing_requests_status", table_name="viewing_requests")
    op.drop_index("ix_viewing_requests_requester_id", table_name="viewing_requests")
    op.drop_index("ix_viewing_requests_property_id", table_name="viewing_requests")
    op.drop_table("viewing_requests")
    op.drop_index("ix_favourite_properties_property_id", table_name="favourite_properties")
    op.drop_index("ix_favourite_properties_user_id", table_name="favourite_properties")
    op.drop_table("favourite_properties")
