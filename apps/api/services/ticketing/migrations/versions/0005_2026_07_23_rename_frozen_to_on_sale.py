"""rename ticket state frozen to on_sale

Revision ID: 0005_rename_frozen_to_on_sale
Revises: 0004_add_holder_to_tickets
Create Date: 2026-07-23

"""
from typing import Union

from alembic import op

revision: str = "0005_rename_frozen_to_on_sale"
down_revision: Union[str, None] = "0004_add_holder_to_tickets"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("UPDATE ticketing.tickets SET state = 'on_sale' WHERE state = 'frozen'")


def downgrade() -> None:
    op.execute("UPDATE ticketing.tickets SET state = 'frozen' WHERE state = 'on_sale'")
