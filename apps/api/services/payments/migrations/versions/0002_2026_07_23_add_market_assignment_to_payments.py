"""add market_assignment_id to payments, make reservation_id nullable

Revision ID: 0002_payments_market_assignment
Revises: 0001_payments_init
Create Date: 2026-07-23 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002_payments_market_assignment"
down_revision: Union[str, None] = "0001_payments_init"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Make reservation_id nullable (was NOT NULL UNIQUE)
    op.alter_column(
        "payments",
        "reservation_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=True,
        schema="payments",
    )

    # Add market_assignment_id
    op.add_column(
        "payments",
        sa.Column("market_assignment_id", postgresql.UUID(as_uuid=True), nullable=True),
        schema="payments",
    )
    op.create_unique_constraint(
        "uq_payments_market_assignment_id",
        "payments",
        ["market_assignment_id"],
        schema="payments",
    )
    op.create_index(
        "ix_payments_market_assignment_id",
        "payments",
        ["market_assignment_id"],
        schema="payments",
    )

    # Exactly one of reservation_id / market_assignment_id must be set
    op.create_check_constraint(
        "ck_payments_context",
        "payments",
        "num_nonnulls(reservation_id, market_assignment_id) = 1",
        schema="payments",
    )


def downgrade() -> None:
    op.drop_constraint("ck_payments_context", "payments", schema="payments")
    op.drop_index("ix_payments_market_assignment_id", table_name="payments", schema="payments")
    op.drop_constraint("uq_payments_market_assignment_id", "payments", schema="payments")
    op.drop_column("payments", "market_assignment_id", schema="payments")
    op.alter_column(
        "payments",
        "reservation_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=False,
        schema="payments",
    )
