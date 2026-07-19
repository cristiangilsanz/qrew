"""add reservation_holders table

Revision ID: 0003_sales_reservation_holders
Revises: 0002_sales_phone_e164
Create Date: 2026-07-19 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003_sales_reservation_holders"
down_revision: Union[str, None] = "0002_sales_phone_e164"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "reservation_holders",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("reservation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("holder_name", sa.String(255), nullable=False),
        sa.Column("holder_dni", sa.String(50), nullable=False),
        sa.CheckConstraint("position >= 1", name="ck_reservation_holders_position"),
        sa.UniqueConstraint("reservation_id", "position", name="uq_reservation_holders_reservation_position"),
        schema="sales",
    )
    op.create_index(
        "ix_reservation_holders_reservation_id",
        "reservation_holders",
        ["reservation_id"],
        schema="sales",
    )


def downgrade() -> None:
    op.drop_index("ix_reservation_holders_reservation_id", table_name="reservation_holders", schema="sales")
    op.drop_table("reservation_holders", schema="sales")
