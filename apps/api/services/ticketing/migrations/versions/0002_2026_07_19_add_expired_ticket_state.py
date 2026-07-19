"""add expired ticket state

Revision ID: 0002_add_expired_ticket_state
Revises: 0001_ticketing_init
Create Date: 2026-07-19 00:00:00.000000

"""

from typing import Sequence, Union

revision: str = "0002_add_expired_ticket_state"
down_revision: Union[str, None] = "0001_ticketing_init"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # state column is VARCHAR(20) with no check constraint — no DDL needed to allow new value
    pass


def downgrade() -> None:
    pass
