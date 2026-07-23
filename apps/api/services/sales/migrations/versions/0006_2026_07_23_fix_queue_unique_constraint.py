"""fix market queue unique constraint to allow rejoin after leave

Revision ID: 0006_sales_fix_queue_rejoin
Revises: 0005_sales_starts_at
Create Date: 2026-07-23 00:00:00.000000
"""

from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "0006_sales_fix_queue_rejoin"
down_revision: Union[str, None] = "0005_sales_starts_at"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop the hard unique constraint that prevents re-joining after leaving
    op.drop_constraint(
        "uq_market_queue_entries_event_user",
        "market_queue_entries",
        schema="sales",
        type_="unique",
    )
    # Add a partial unique index: only one active entry per (event_id, user_id)
    op.execute(
        """
        CREATE UNIQUE INDEX uq_market_queue_entries_active_event_user
        ON sales.market_queue_entries (event_id, user_id)
        WHERE left_at IS NULL
        """
    )


def downgrade() -> None:
    op.execute(
        "DROP INDEX IF EXISTS sales.uq_market_queue_entries_active_event_user"
    )
    op.create_unique_constraint(
        "uq_market_queue_entries_event_user",
        "market_queue_entries",
        ["event_id", "user_id"],
        schema="sales",
    )
