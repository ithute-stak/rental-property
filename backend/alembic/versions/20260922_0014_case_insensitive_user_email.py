"""enforce case-insensitive user email uniqueness

Revision ID: 20260922_0014
Revises: 20260922_0013
Create Date: 2026-09-22
"""

from alembic import op

revision = "20260922_0014"
down_revision = "20260922_0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE UNIQUE INDEX uq_users_email_lower
        ON users (lower(email))
        WHERE email IS NOT NULL
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_users_email_lower")
