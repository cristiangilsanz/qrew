"""add price_cents and currency to ticket_type_inventory

Revision ID: c2d3e4f5a6b7
Revises: b1c2d3e4f5a6
Create Date: 2026-06-14 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op

revision: str = "c2d3e4f5a6b7"
down_revision: Union[str, None] = "b1c2d3e4f5a6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE sales.ticket_type_inventory
            ADD COLUMN IF NOT EXISTS price_cents INTEGER NOT NULL DEFAULT 0,
            ADD COLUMN IF NOT EXISTS currency VARCHAR(3) NOT NULL DEFAULT 'EUR'
    """)


def downgrade() -> None:
    op.execute("""
        ALTER TABLE sales.ticket_type_inventory
            DROP COLUMN IF EXISTS price_cents,
            DROP COLUMN IF EXISTS currency
    """)
