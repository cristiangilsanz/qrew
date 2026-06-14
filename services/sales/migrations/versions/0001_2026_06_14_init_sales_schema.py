"""init sales schema

Revision ID: b1c2d3e4f5a6
Revises:
Create Date: 2026-06-14 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op

revision: str = "b1c2d3e4f5a6"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS sales")

    op.execute("""
        CREATE TABLE IF NOT EXISTS sales.reservations (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID NOT NULL,
            event_id UUID NOT NULL,
            ticket_type_id UUID NOT NULL,
            quantity INTEGER NOT NULL CHECK (quantity >= 1),
            status VARCHAR(16) NOT NULL DEFAULT 'reserved',
            expires_at TIMESTAMPTZ NOT NULL,
            requires_review BOOLEAN NOT NULL DEFAULT false,
            risk_score INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)

    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_reservations_user_id
            ON sales.reservations (user_id)
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_reservations_event_id
            ON sales.reservations (event_id)
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_reservations_status_expires_at
            ON sales.reservations (status, expires_at)
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS sales.event_context (
            event_id UUID PRIMARY KEY,
            status VARCHAR(32) NOT NULL,
            sale_starts_at TIMESTAMPTZ,
            sale_ends_at TIMESTAMPTZ,
            max_tickets_per_user INTEGER NOT NULL DEFAULT 10,
            queue_required BOOLEAN NOT NULL DEFAULT false,
            queue_admit_rate_per_minute INTEGER NOT NULL DEFAULT 50,
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS sales.ticket_type_inventory (
            ticket_type_id UUID PRIMARY KEY,
            event_id UUID NOT NULL,
            capacity INTEGER NOT NULL,
            reserved_count INTEGER NOT NULL DEFAULT 0,
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_ticket_type_inventory_event_id
            ON sales.ticket_type_inventory (event_id)
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS sales.user_age_context (
            user_id UUID PRIMARY KEY,
            registered_at TIMESTAMPTZ NOT NULL,
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS sales.fingerprint_context (
            fingerprint_hash VARCHAR(128) PRIMARY KEY,
            distinct_user_count INTEGER NOT NULL DEFAULT 1,
            last_seen_at TIMESTAMPTZ NOT NULL,
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS sales.fingerprint_context")
    op.execute("DROP TABLE IF EXISTS sales.user_age_context")
    op.execute("DROP TABLE IF EXISTS sales.ticket_type_inventory")
    op.execute("DROP TABLE IF EXISTS sales.event_context")
    op.execute("DROP TABLE IF EXISTS sales.reservations")
    op.execute("DROP SCHEMA IF EXISTS sales")
