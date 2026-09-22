"""add property media

Revision ID: 20260922_0003
Revises: 20260922_0002
Create Date: 2026-09-22
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260922_0003"
down_revision = "20260922_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "property_media",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "property_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("properties.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "unit_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("units.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("object_key", sa.String(500), nullable=False),
        sa.Column("content_type", sa.String(100), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_cover", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("object_key", name="uq_property_media_object_key"),
    )
    op.create_index("ix_property_media_property_id", "property_media", ["property_id"])
    op.create_index("ix_property_media_unit_id", "property_media", ["unit_id"])
    op.create_index("ix_property_media_is_cover", "property_media", ["is_cover"])


def downgrade() -> None:
    op.drop_index("ix_property_media_is_cover", table_name="property_media")
    op.drop_index("ix_property_media_unit_id", table_name="property_media")
    op.drop_index("ix_property_media_property_id", table_name="property_media")
    op.drop_table("property_media")
