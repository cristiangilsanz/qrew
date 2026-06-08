"""2026_06_09_add_payments_table

Revision ID: c6d7e8f9a0b1
Revises: b5c6d7e8f9a0
Create Date: 2026-06-09 03:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "c6d7e8f9a0b1"
down_revision: str | None = "b5c6d7e8f9a0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "payments",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "reservation_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("reservations.id", ondelete="RESTRICT"),
            nullable=False,
            unique=True,
        ),
        sa.Column("provider", sa.String(32), nullable=False, server_default="stripe"),
        sa.Column("provider_payment_intent_id", sa.String(255), nullable=True),
        sa.Column("amount_cents", sa.Integer, nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default="requires_action",
        ),
        sa.Column("client_secret_ciphertext", sa.LargeBinary, nullable=True),
        sa.Column("failure_code", sa.String(64), nullable=True),
        sa.Column("failure_message", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint("amount_cents >= 0", name="ck_payments_amount"),
        sa.CheckConstraint(
            "status IN ('requires_action','processing','succeeded','failed','refunded')",
            name="ck_payments_status",
        ),
    )
    op.create_index(
        "ix_payments_provider_payment_intent_id",
        "payments",
        ["provider_payment_intent_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_payments_provider_payment_intent_id", table_name="payments")
    op.drop_table("payments")
