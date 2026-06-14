"""init identity schema

Revision ID: 0001_identity_init
Revises:
Create Date: 2026-06-14

Baseline migration for the identity service.  All tables in the `identity` and
`audit` schemas were originally created by the monolith's alembic migrations.
This migration creates the schemas so that autogenerate compares correctly on
fresh environments.  On an existing database where the monolith already ran,
stamp this migration with `alembic stamp 0001_identity_init` before deleting the
monolith.
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
