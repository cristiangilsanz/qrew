"""rename ticket states entry_pending->scanning and used->redeemed

Revision ID: 0006_rename_entry_pending_and_used
Revises: 0005_rename_frozen_to_on_sale
Create Date: 2026-07-23

"""

from typing import Union

from alembic import op

revision: str = "0006_rename_entry_pending_and_used"
down_revision: Union[str, None] = "0005_rename_frozen_to_on_sale"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE alembic_version_ticketing ALTER COLUMN version_num TYPE VARCHAR(50)")
    op.execute("UPDATE ticketing.tickets SET state = 'scanning' WHERE state = 'entry_pending'")
    op.execute("UPDATE ticketing.tickets SET state = 'redeemed' WHERE state = 'used'")


def downgrade() -> None:
    op.execute("UPDATE ticketing.tickets SET state = 'entry_pending' WHERE state = 'scanning'")
    op.execute("UPDATE ticketing.tickets SET state = 'used' WHERE state = 'redeemed'")
