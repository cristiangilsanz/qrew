"""2026_06_09_add_reservation_risk_columns

Revision ID: b5c6d7e8f9a0
Revises: a4b5c6d7e8f9
Create Date: 2026-06-09 02:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b5c6d7e8f9a0"
down_revision: str | None = "a4b5c6d7e8f9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "reservations",
        sa.Column(
            "requires_review",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "reservations",
        sa.Column(
            "risk_score",
            sa.Integer,
            nullable=False,
            server_default="0",
        ),
    )
    op.execute(
        "CREATE OR REPLACE VIEW flagged_reservations AS "
        "SELECT r.id, r.user_id, r.event_id, r.ticket_type_id, r.quantity, "
        "r.status, r.risk_score, r.created_at "
        "FROM reservations r WHERE r.requires_review = true"
    )


def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS flagged_reservations")
    op.drop_column("reservations", "risk_score")
    op.drop_column("reservations", "requires_review")
