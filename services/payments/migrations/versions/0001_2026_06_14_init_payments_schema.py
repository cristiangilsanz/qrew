"""init payments schema

Revision ID: b1c2d3e4f5a6
Revises:
Create Date: 2026-06-14 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "b1c2d3e4f5a6"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS payments")

    op.create_table(
        "payments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reservation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider", sa.String(32), nullable=False, server_default="stripe"),
        sa.Column("provider_payment_intent_id", sa.String(255), nullable=True),
        sa.Column("amount_cents", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default="requires_action",
        ),
        sa.Column("client_secret_ciphertext", sa.LargeBinary(), nullable=True),
        sa.Column("failure_code", sa.String(64), nullable=True),
        sa.Column("failure_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("amount_cents >= 0", name="ck_payments_amount"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("reservation_id", name="uq_payments_reservation_id"),
        schema="payments",
    )
    op.create_index(
        "ix_payments_provider_payment_intent_id",
        "payments",
        ["provider_payment_intent_id"],
        schema="payments",
    )


def downgrade() -> None:
    op.drop_table("payments", schema="payments")
    op.execute("DROP SCHEMA IF EXISTS payments CASCADE")
