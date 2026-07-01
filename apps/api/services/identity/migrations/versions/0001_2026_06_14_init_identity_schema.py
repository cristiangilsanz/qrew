"""init identity schema

Revision ID: 0001_identity_init
Revises:
Create Date: 2026-06-14 00:00:00.000000

"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0001_identity_init"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS identity")
    op.execute("CREATE SCHEMA IF NOT EXISTS audit")


def downgrade() -> None:
    pass
