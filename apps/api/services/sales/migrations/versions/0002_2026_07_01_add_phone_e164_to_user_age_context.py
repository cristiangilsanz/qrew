"""add phone_e164 to user_age_context

Revision ID: 0002_sales_phone_e164
Revises: 0001_sales_init
Create Date: 2026-07-01 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op

revision: str = "0002_sales_phone_e164"
down_revision: Union[str, None] = "0001_sales_init"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE sales.user_age_context
            ADD COLUMN IF NOT EXISTS phone_e164 VARCHAR(32)
    """)


def downgrade() -> None:
    op.execute("""
        ALTER TABLE sales.user_age_context
            DROP COLUMN IF EXISTS phone_e164
    """)
