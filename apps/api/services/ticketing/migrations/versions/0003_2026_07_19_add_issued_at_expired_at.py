"""add issued_at and expired_at to tickets

Revision ID: 0003_add_issued_at_expired_at
Revises: 0002_add_expired_ticket_state
Create Date: 2026-07-19 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003_add_issued_at_expired_at"
down_revision: Union[str, None] = "0002_add_expired_ticket_state"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "tickets",
        sa.Column("issued_at", sa.DateTime(timezone=True), nullable=True),
        schema="ticketing",
    )
    op.add_column(
        "tickets",
        sa.Column("expired_at", sa.DateTime(timezone=True), nullable=True),
        schema="ticketing",
    )


def downgrade() -> None:
    op.drop_column("tickets", "expired_at", schema="ticketing")
    op.drop_column("tickets", "issued_at", schema="ticketing")
