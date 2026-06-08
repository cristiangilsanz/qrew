"""2026_06_09_add_event_queue_columns

Revision ID: a4b5c6d7e8f9
Revises: f3a4b5c6d7e8
Create Date: 2026-06-09 01:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a4b5c6d7e8f9"
down_revision: str | None = "f3a4b5c6d7e8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "events",
        sa.Column(
            "queue_required",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "events",
        sa.Column(
            "queue_admit_rate_per_minute",
            sa.Integer,
            nullable=False,
            server_default="60",
        ),
    )
    op.create_check_constraint(
        "ck_events_queue_admit_rate",
        "events",
        "queue_admit_rate_per_minute >= 1 AND queue_admit_rate_per_minute <= 600",
    )


def downgrade() -> None:
    op.drop_constraint("ck_events_queue_admit_rate", "events", type_="check")
    op.drop_column("events", "queue_admit_rate_per_minute")
    op.drop_column("events", "queue_required")
