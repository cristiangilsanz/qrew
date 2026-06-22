"""add entry.scans table

Revision ID: 0002_entry_scans
Revises: 0001_entry_init
Create Date: 2026-06-20 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002_entry_scans"
down_revision: str | None = "0001_entry_init"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "scans",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ticket_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("scanner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("allowed", sa.Boolean(), nullable=False),
        sa.Column("reason", sa.String(32), nullable=True),
        sa.Column("scanned_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        schema="entry",
    )
    op.create_index("ix_entry_scans_event_id", "scans", ["event_id"], schema="entry")
    op.create_index(
        "ix_entry_scans_event_scanned_at",
        "scans",
        ["event_id", "scanned_at"],
        schema="entry",
    )


def downgrade() -> None:
    op.drop_index("ix_entry_scans_event_scanned_at", table_name="scans", schema="entry")
    op.drop_index("ix_entry_scans_event_id", table_name="scans", schema="entry")
    op.drop_table("scans", schema="entry")
