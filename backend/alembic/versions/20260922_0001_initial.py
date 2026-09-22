"""initial rental marketplace schema

Revision ID: 20260922_0001
Revises:
Create Date: 2026-09-22
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from geoalchemy2 import Geography

revision = "20260922_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(320), nullable=True, unique=True),
        sa.Column("phone", sa.String(32), nullable=False, unique=True),
        sa.Column("display_name", sa.String(160), nullable=False),
        sa.Column("role", sa.String(32), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "properties",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(180), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("property_type", sa.String(40), nullable=False),
        sa.Column("status", sa.String(40), nullable=False),
        sa.Column("physical_address", sa.String(500), nullable=False),
        sa.Column("district", sa.String(100), nullable=False),
        sa.Column("town", sa.String(100), nullable=False),
        sa.Column("area", sa.String(120), nullable=True),
        sa.Column("latitude", sa.Numeric(9, 6), nullable=False),
        sa.Column("longitude", sa.Numeric(9, 6), nullable=False),
        sa.Column("location", Geography(geometry_type="POINT", srid=4326, spatial_index=True), nullable=False),
        sa.Column("total_rooms", sa.Integer(), nullable=False),
        sa.Column("security_level", sa.String(40), nullable=False),
        sa.Column("security_features", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("total_rooms > 0", name="ck_properties_total_rooms_positive"),
    )
    op.create_index("ix_properties_status", "properties", ["status"])
    op.create_index("ix_properties_district_town", "properties", ["district", "town"])

    op.create_table(
        "units",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("property_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("properties.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("monthly_rent", sa.Numeric(12, 2), nullable=False),
        sa.Column("deposit", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("status", sa.String(40), nullable=False),
        sa.Column("available_from", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("monthly_rent >= 0", name="ck_units_monthly_rent_nonnegative"),
        sa.CheckConstraint("deposit >= 0", name="ck_units_deposit_nonnegative"),
    )
    op.create_index("ix_units_property_status", "units", ["property_id", "status"])


def downgrade() -> None:
    op.drop_table("units")
    op.drop_table("properties")
    op.drop_table("users")
