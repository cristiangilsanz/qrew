"""add user_id to payments

Revision ID: c2d3e4f5a6b8
Revises: b1c2d3e4f5a6
Create Date: 2026-06-14 00:00:00.000000

"""

from collections.abc import Sequence

from alembic import op

revision: str = "c2d3e4f5a6b8"
down_revision: str | None = "b1c2d3e4f5a6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE payments.payments
            ADD COLUMN IF NOT EXISTS user_id UUID
    """)


def downgrade() -> None:
    op.execute("""
        ALTER TABLE payments.payments
            DROP COLUMN IF EXISTS user_id
    """)
