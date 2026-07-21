"""add outbox table

Revision ID: 0003_add_outbox_table
Revises: 29ca6f230f31
Create Date: 2026-07-21 00:00:00.000000

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003_add_outbox_table"
down_revision: str | None = "29ca6f230f31"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "outbox",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("aggregate_type", sa.String(length=64), nullable=False),
        sa.Column("aggregate_id", sa.String(length=64), nullable=False),
        sa.Column("job_name", sa.String(length=64), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("dispatched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column(
            "next_attempt_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("dlq_reason", sa.String(length=64), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        schema="identity",
    )
    op.create_index(
        "ix_identity_outbox_next_attempt_at",
        "outbox",
        ["next_attempt_at"],
        unique=False,
        schema="identity",
    )
    op.create_index(
        "ix_identity_outbox_dlq_reason",
        "outbox",
        ["dlq_reason"],
        unique=False,
        schema="identity",
    )


def downgrade() -> None:
    op.drop_index("ix_identity_outbox_dlq_reason", table_name="outbox", schema="identity")
    op.drop_index("ix_identity_outbox_next_attempt_at", table_name="outbox", schema="identity")
    op.drop_table("outbox", schema="identity")
