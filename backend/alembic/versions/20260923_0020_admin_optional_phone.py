"""Allow email-only administrator accounts.

Revision ID: 20260923_0020
Revises: 20260923_0019
Create Date: 2026-09-23

Public landlord and house-seeker registration continues to require a phone number.
This migration only relaxes the database column so an operational administrator can
be provisioned with an email identity without inventing fake phone data.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260923_0020"
down_revision: str | None = "20260923_0019"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "users",
        "phone",
        existing_type=sa.String(length=32),
        nullable=True,
    )


def downgrade() -> None:
    # Preserve rollbackability without losing administrator rows that were created
    # email-only. UUID-derived values remain unique and fit the 32-character column.
    op.execute(
        """
        UPDATE users
        SET phone = 'adm-' || left(replace(id::text, '-', ''), 28)
        WHERE phone IS NULL
        """
    )
    op.alter_column(
        "users",
        "phone",
        existing_type=sa.String(length=32),
        nullable=False,
    )
