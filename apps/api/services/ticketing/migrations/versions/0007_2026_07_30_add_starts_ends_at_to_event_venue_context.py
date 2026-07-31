"""add starts_at and ends_at to event_venue_context

Revision ID: 0007_add_starts_ends_at_event_venue_ctx
Revises: 0006_rename_entry_pending_and_used
Create Date: 2026-07-30 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0007_add_starts_ends_at_event_venue_ctx"
down_revision: Union[str, None] = "0006_rename_states"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "event_venue_context",
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=True),
        schema="ticketing",
    )
    op.add_column(
        "event_venue_context",
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True),
        schema="ticketing",
    )


def downgrade() -> None:
    op.drop_column("event_venue_context", "ends_at", schema="ticketing")
    op.drop_column("event_venue_context", "starts_at", schema="ticketing")
