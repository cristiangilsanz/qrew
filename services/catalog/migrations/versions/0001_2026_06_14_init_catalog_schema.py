"""init catalog schema

Revision ID: c1a2b3d4e5f6
Revises:
Create Date: 2026-06-14 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op

revision: str = "c1a2b3d4e5f6"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS catalog")

    op.execute("""
        CREATE TABLE IF NOT EXISTS catalog.organisations (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            slug VARCHAR(64) NOT NULL,
            name VARCHAR(128) NOT NULL,
            description TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            deleted_at TIMESTAMPTZ
        )
    """)
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_organisations_slug ON catalog.organisations (slug)"
    )

    op.execute("""
        CREATE TABLE IF NOT EXISTS catalog.organisation_members (
            organisation_id UUID NOT NULL REFERENCES catalog.organisations(id) ON DELETE CASCADE,
            user_id UUID NOT NULL,
            role VARCHAR(16) NOT NULL DEFAULT 'member',
            joined_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            PRIMARY KEY (organisation_id, user_id)
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS catalog.venues (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name VARCHAR(128) NOT NULL,
            address_line VARCHAR(256) NOT NULL,
            city VARCHAR(96) NOT NULL,
            country CHAR(2) NOT NULL,
            latitude NUMERIC(9,6) NOT NULL,
            longitude NUMERIC(9,6) NOT NULL,
            geofence_radius_m INTEGER NOT NULL DEFAULT 200,
            timezone VARCHAR(64) NOT NULL,
            description TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            deleted_at TIMESTAMPTZ
        )
    """)
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_venues_city_country ON catalog.venues (city, country)"
    )

    op.execute("""
        CREATE TABLE IF NOT EXISTS catalog.events (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            organisation_id UUID NOT NULL REFERENCES catalog.organisations(id) ON DELETE RESTRICT,
            venue_id UUID NOT NULL REFERENCES catalog.venues(id) ON DELETE RESTRICT,
            name VARCHAR(160) NOT NULL,
            description TEXT,
            starts_at TIMESTAMPTZ NOT NULL,
            ends_at TIMESTAMPTZ NOT NULL,
            sale_starts_at TIMESTAMPTZ NOT NULL,
            sale_ends_at TIMESTAMPTZ NOT NULL,
            max_tickets_per_user INTEGER NOT NULL DEFAULT 4,
            status VARCHAR(16) NOT NULL DEFAULT 'draft',
            organiser_name VARCHAR(128) NOT NULL,
            venue_city VARCHAR(96) NOT NULL,
            queue_required BOOLEAN NOT NULL DEFAULT false,
            queue_admit_rate_per_minute INTEGER NOT NULL DEFAULT 60,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            published_at TIMESTAMPTZ,
            cancelled_at TIMESTAMPTZ,
            search_vector TSVECTOR,
            CONSTRAINT ck_events_time_window CHECK (starts_at < ends_at),
            CONSTRAINT ck_events_sale_window CHECK (sale_starts_at < sale_ends_at),
            CONSTRAINT ck_events_sale_before_start CHECK (sale_ends_at <= starts_at),
            CONSTRAINT ck_events_max_tickets CHECK (max_tickets_per_user >= 1 AND max_tickets_per_user <= 20),
            CONSTRAINT ck_events_queue_admit_rate CHECK (queue_admit_rate_per_minute >= 1 AND queue_admit_rate_per_minute <= 600)
        )
    """)
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_events_organisation_id ON catalog.events (organisation_id)"
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_events_venue_id ON catalog.events (venue_id)")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_events_status_starts_at ON catalog.events (status, starts_at)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_events_search_vector ON catalog.events USING gin (search_vector)"
    )

    op.execute("""
        CREATE TABLE IF NOT EXISTS catalog.ticket_types (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            event_id UUID NOT NULL REFERENCES catalog.events(id) ON DELETE RESTRICT,
            name VARCHAR(32) NOT NULL,
            description TEXT,
            capacity INTEGER NOT NULL,
            reserved_count INTEGER NOT NULL DEFAULT 0,
            price_cents INTEGER NOT NULL,
            currency CHAR(3) NOT NULL,
            position INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            deleted_at TIMESTAMPTZ,
            CONSTRAINT uq_ticket_types_event_name UNIQUE (event_id, name),
            CONSTRAINT ck_ticket_types_capacity CHECK (capacity >= 1 AND capacity <= 100000),
            CONSTRAINT ck_ticket_types_reserved CHECK (reserved_count >= 0 AND reserved_count <= capacity),
            CONSTRAINT ck_ticket_types_price CHECK (price_cents >= 0 AND price_cents <= 10000000)
        )
    """)
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_ticket_types_event_id ON catalog.ticket_types (event_id)"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS catalog.ticket_types")
    op.execute("DROP TABLE IF EXISTS catalog.events")
    op.execute("DROP TABLE IF EXISTS catalog.venues")
    op.execute("DROP TABLE IF EXISTS catalog.organisation_members")
    op.execute("DROP TABLE IF EXISTS catalog.organisations")
    op.execute("DROP SCHEMA IF EXISTS catalog CASCADE")
