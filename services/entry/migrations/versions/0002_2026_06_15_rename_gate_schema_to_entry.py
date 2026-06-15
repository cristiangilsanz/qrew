"""rename gate schema to entry

Revision ID: b2c3d4e5f6a1
Revises: a1b2c3d4e5f6
Create Date: 2026-06-15 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op

revision: str = "b2c3d4e5f6a1"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER SCHEMA gate RENAME TO entry")


def downgrade() -> None:
    op.execute("ALTER SCHEMA entry RENAME TO gate")
