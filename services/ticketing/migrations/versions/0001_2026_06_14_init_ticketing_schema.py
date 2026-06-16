"""init ticketing schema

Revision ID: 0001_ticketing_init
Revises:
Create Date: 2026-06-14 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op

revision: str = "0001_ticketing_init"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS ticketing")

    op.execute("""
        CREATE TABLE IF NOT EXISTS ticketing.tickets (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            reservation_id UUID NOT NULL,
            event_id UUID NOT NULL,
            ticket_type_id UUID NOT NULL,
            owner_user_id UUID NOT NULL,
            bound_device_id UUID,
            state VARCHAR(20) NOT NULL DEFAULT 'reserved',
            state_updated_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_tickets_reservation_id ON ticketing.tickets (reservation_id)"
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_tickets_event_id ON ticketing.tickets (event_id)")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_tickets_owner_user_id ON ticketing.tickets (owner_user_id)"
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_tickets_state ON ticketing.tickets (state)")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_tickets_bound_device_id ON ticketing.tickets (bound_device_id)"
    )

    op.execute("""
        CREATE TABLE IF NOT EXISTS ticketing.event_venue_context (
            event_id UUID PRIMARY KEY,
            venue_id UUID NOT NULL,
            event_status VARCHAR(16) NOT NULL DEFAULT 'draft',
            latitude NUMERIC(9,6) NOT NULL DEFAULT 0,
            longitude NUMERIC(9,6) NOT NULL DEFAULT 0,
            geofence_radius_m INTEGER NOT NULL DEFAULT 200,
            timezone VARCHAR(64) NOT NULL DEFAULT 'UTC',
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS ticketing.device_context (
            device_id UUID PRIMARY KEY,
            user_id UUID NOT NULL,
            attested_at TIMESTAMPTZ,
            revoked_at TIMESTAMPTZ,
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_device_context_user_id ON ticketing.device_context (user_id)"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS ticketing.device_context")
    op.execute("DROP TABLE IF EXISTS ticketing.event_venue_context")
    op.execute("DROP TABLE IF EXISTS ticketing.tickets")
    op.execute("DROP SCHEMA IF EXISTS ticketing")
