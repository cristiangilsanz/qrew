"""init payments schema (squashed)

Revision ID: 0001_payments_init
Revises:
Create Date: 2026-08-04 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_payments_init"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# creates the payments schema and its tables
def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS payments")

    op.execute("""
        CREATE TABLE IF NOT EXISTS payments.event_outbox (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            subject VARCHAR(128) NOT NULL,
            aggregate_type VARCHAR(64) NOT NULL,
            aggregate_id VARCHAR(64) NOT NULL,
            actor_id VARCHAR(64),
            payload JSONB NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            dispatched_at TIMESTAMPTZ,
            attempt_count INTEGER NOT NULL DEFAULT 0,
            last_error TEXT,
            next_attempt_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            dlq_reason VARCHAR(64)
        )
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_payments_event_outbox_pending
            ON payments.event_outbox (next_attempt_at)
            WHERE dispatched_at IS NULL AND dlq_reason IS NULL
    """)

    op.create_table(
        "payments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reservation_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("market_assignment_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
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
        sa.CheckConstraint(
            "num_nonnulls(reservation_id, market_assignment_id) = 1",
            name="ck_payments_context",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("reservation_id", name="uq_payments_reservation_id"),
        sa.UniqueConstraint("market_assignment_id", name="uq_payments_market_assignment_id"),
        schema="payments",
    )
    op.create_index(
        "ix_payments_provider_payment_intent_id",
        "payments",
        ["provider_payment_intent_id"],
        schema="payments",
    )
    op.create_index(
        "ix_payments_market_assignment_id",
        "payments",
        ["market_assignment_id"],
        schema="payments",
    )


# drops the payments schema and its tables
def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS payments.event_outbox")
    op.drop_index("ix_payments_market_assignment_id", table_name="payments", schema="payments")
    op.drop_index(
        "ix_payments_provider_payment_intent_id", table_name="payments", schema="payments"
    )
    op.drop_table("payments", schema="payments")
    op.execute("DROP SCHEMA IF EXISTS payments CASCADE")
