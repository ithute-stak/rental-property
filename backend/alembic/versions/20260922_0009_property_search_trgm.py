"""add typo tolerant property search indexes

Revision ID: 20260922_0009
Revises: 20260922_0008
Create Date: 2026-09-22
"""

from alembic import op

revision = "20260922_0009"
down_revision = "20260922_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.execute(
        "CREATE INDEX ix_properties_title_trgm ON properties USING gin (title gin_trgm_ops)"
    )
    op.execute(
        "CREATE INDEX ix_properties_area_trgm ON properties USING gin (area gin_trgm_ops)"
    )
    op.execute(
        "CREATE INDEX ix_properties_town_trgm ON properties USING gin (town gin_trgm_ops)"
    )
    op.execute(
        "CREATE INDEX ix_properties_district_trgm ON properties USING gin (district gin_trgm_ops)"
    )
    op.execute(
        "CREATE INDEX ix_properties_physical_address_trgm "
        "ON properties USING gin (physical_address gin_trgm_ops)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_properties_physical_address_trgm")
    op.execute("DROP INDEX IF EXISTS ix_properties_district_trgm")
    op.execute("DROP INDEX IF EXISTS ix_properties_town_trgm")
    op.execute("DROP INDEX IF EXISTS ix_properties_area_trgm")
    op.execute("DROP INDEX IF EXISTS ix_properties_title_trgm")
