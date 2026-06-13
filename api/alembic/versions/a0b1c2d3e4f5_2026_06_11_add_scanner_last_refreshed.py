"""2026_06_11_add_scanner_last_refreshed

Revision ID: a0b1c2d3e4f5
Revises: f9a0b1c2d3e4
Create Date: 2026-06-11 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a0b1c2d3e4f5"
down_revision: str | None = "f9a0b1c2d3e4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "scanners",
        sa.Column("last_refreshed_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("scanners", "last_refreshed_at")
