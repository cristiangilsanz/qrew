"""add holder_name and holder_dni to tickets

Revision ID: 0004_add_holder_fields_to_tickets
Revises: 0003_add_issued_at_expired_at
Create Date: 2026-07-19 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004_add_holder_to_tickets"
down_revision: Union[str, None] = "0003_add_issued_at_expired_at"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "tickets",
        sa.Column("holder_name", sa.String(255), nullable=True),
        schema="ticketing",
    )
    op.add_column(
        "tickets",
        sa.Column("holder_dni", sa.String(50), nullable=True),
        schema="ticketing",
    )


def downgrade() -> None:
    op.drop_column("tickets", "holder_dni", schema="ticketing")
    op.drop_column("tickets", "holder_name", schema="ticketing")
