"""init entry schema

Revision ID: 0001_entry_init
Revises:
Create Date: 2026-06-13 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_entry_init"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS entry")

    op.create_table(
        "scanners",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("venue_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_refreshed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
        schema="entry",
    )
    op.create_index(
        "ix_entry_scanners_venue_id", "scanners", ["venue_id"], schema="entry"
    )
    op.create_index(
        "ix_entry_scanners_created_by", "scanners", ["created_by"], schema="entry"
    )

    op.create_table(
        "ticket_contexts",
        sa.Column("ticket_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("venue_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("owner_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("bound_device_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("state", sa.String(32), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("ticket_id"),
        schema="entry",
    )
    op.create_index(
        "ix_entry_ticket_contexts_event_id",
        "ticket_contexts",
        ["event_id"],
        schema="entry",
    )
    op.create_index(
        "ix_entry_ticket_contexts_state",
        "ticket_contexts",
        ["state"],
        schema="entry",
    )


def downgrade() -> None:
    op.drop_table("ticket_contexts", schema="entry")
    op.drop_table("scanners", schema="entry")
    op.execute("DROP SCHEMA IF EXISTS entry")
