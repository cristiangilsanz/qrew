"""init sales schema (squashed)

Revision ID: 0001_sales_init
Revises:
Create Date: 2026-08-04 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_sales_init"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# creates the sales schema and its tables
def upgrade() -> None:
    # ------------------------------------------------------------------
    # Schema
    # ------------------------------------------------------------------
    op.execute("CREATE SCHEMA IF NOT EXISTS sales")

    # ------------------------------------------------------------------
    # reservations
    # ------------------------------------------------------------------
    op.execute("""
        CREATE TABLE IF NOT EXISTS sales.reservations (
            id               UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id          UUID         NOT NULL,
            event_id         UUID         NOT NULL,
            ticket_type_id   UUID         NOT NULL,
            quantity         INTEGER      NOT NULL CHECK (quantity >= 1),
            status           VARCHAR(16)  NOT NULL DEFAULT 'reserved',
            expires_at       TIMESTAMPTZ  NOT NULL,
            requires_review  BOOLEAN      NOT NULL DEFAULT false,
            risk_score       INTEGER      NOT NULL DEFAULT 0,
            created_at       TIMESTAMPTZ  NOT NULL DEFAULT now(),
            updated_at       TIMESTAMPTZ  NOT NULL DEFAULT now()
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

    # ------------------------------------------------------------------
    # event_context  (projection)
    # starts_at was added in migration 0005 — included here in final state
    # ------------------------------------------------------------------
    op.execute("""
        CREATE TABLE IF NOT EXISTS sales.event_context (
            event_id                    UUID         PRIMARY KEY,
            status                      VARCHAR(32)  NOT NULL,
            starts_at                   TIMESTAMPTZ,
            sale_starts_at              TIMESTAMPTZ,
            sale_ends_at                TIMESTAMPTZ,
            max_tickets_per_user        INTEGER      NOT NULL DEFAULT 10,
            queue_required              BOOLEAN      NOT NULL DEFAULT false,
            queue_admit_rate_per_minute INTEGER      NOT NULL DEFAULT 50,
            updated_at                  TIMESTAMPTZ  NOT NULL DEFAULT now()
        )
    """)

    # ------------------------------------------------------------------
    # ticket_type_inventory  (projection)
    # ------------------------------------------------------------------
    op.execute("""
        CREATE TABLE IF NOT EXISTS sales.ticket_type_inventory (
            ticket_type_id  UUID        PRIMARY KEY,
            event_id        UUID        NOT NULL,
            capacity        INTEGER     NOT NULL,
            reserved_count  INTEGER     NOT NULL DEFAULT 0,
            price_cents     INTEGER     NOT NULL DEFAULT 0,
            currency        VARCHAR(3)  NOT NULL DEFAULT 'EUR',
            updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_ticket_type_inventory_event_id
            ON sales.ticket_type_inventory (event_id)
    """)

    # ------------------------------------------------------------------
    # user_age_context  (projection)
    # phone_e164 was added in migration 0002 — included here in final state
    # ------------------------------------------------------------------
    op.execute("""
        CREATE TABLE IF NOT EXISTS sales.user_age_context (
            user_id       UUID        PRIMARY KEY,
            registered_at TIMESTAMPTZ NOT NULL,
            phone_e164    VARCHAR(32),
            updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)

    # ------------------------------------------------------------------
    # fingerprint_context  (projection)
    # ------------------------------------------------------------------
    op.execute("""
        CREATE TABLE IF NOT EXISTS sales.fingerprint_context (
            fingerprint_hash    VARCHAR(128) PRIMARY KEY,
            distinct_user_count INTEGER      NOT NULL DEFAULT 1,
            last_seen_at        TIMESTAMPTZ  NOT NULL,
            updated_at          TIMESTAMPTZ  NOT NULL DEFAULT now()
        )
    """)

    # ------------------------------------------------------------------
    # reservation_holders
    # ------------------------------------------------------------------
    op.create_table(
        "reservation_holders",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("reservation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("holder_name", sa.String(255), nullable=False),
        sa.Column("holder_dni", sa.String(50), nullable=False),
        sa.CheckConstraint("position >= 1", name="ck_reservation_holders_position"),
        sa.UniqueConstraint(
            "reservation_id", "position", name="uq_reservation_holders_reservation_position"
        ),
        schema="sales",
    )
    op.create_index(
        "ix_reservation_holders_reservation_id",
        "reservation_holders",
        ["reservation_id"],
        schema="sales",
    )

    # ------------------------------------------------------------------
    # market_queue_entries
    # No hard unique constraint on (event_id, user_id); a partial unique
    # index (WHERE left_at IS NULL) is used instead to allow re-join after
    # leaving (migration 0006 dropped the original full unique constraint).
    # ------------------------------------------------------------------
    op.create_table(
        "market_queue_entries",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tiebreak", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "joined_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("left_at", sa.DateTime(timezone=True), nullable=True),
        schema="sales",
    )
    op.create_index(
        "ix_market_queue_entries_event_id_active",
        "market_queue_entries",
        ["event_id"],
        schema="sales",
        postgresql_where=sa.text("left_at IS NULL"),
    )
    op.create_index(
        "ix_market_queue_entries_user_id",
        "market_queue_entries",
        ["user_id"],
        schema="sales",
    )
    # Partial unique index: at most one active entry per (event_id, user_id)
    op.execute("""
        CREATE UNIQUE INDEX uq_market_queue_entries_active_event_user
            ON sales.market_queue_entries (event_id, user_id)
            WHERE left_at IS NULL
    """)

    # ------------------------------------------------------------------
    # market_listings
    # ------------------------------------------------------------------
    op.create_table(
        "market_listings",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("ticket_id", postgresql.UUID(as_uuid=True), nullable=False, unique=True),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("seller_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ticket_type_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("price_cents", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="EUR"),
        sa.Column("state", sa.String(32), nullable=False, server_default="available"),
        sa.Column(
            "listed_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("price_cents >= 0", name="ck_market_listings_price"),
        sa.CheckConstraint(
            "state IN ('available', 'assigned', 'completed', 'cancelled')",
            name="ck_market_listings_state",
        ),
        schema="sales",
    )
    op.create_index(
        "ix_market_listings_event_id_state",
        "market_listings",
        ["event_id", "state"],
        schema="sales",
    )
    op.create_index(
        "ix_market_listings_seller_user_id",
        "market_listings",
        ["seller_user_id"],
        schema="sales",
    )
    op.create_index(
        "ix_market_listings_expires_at_state",
        "market_listings",
        ["expires_at", "state"],
        schema="sales",
        postgresql_where=sa.text("state IN ('available', 'assigned')"),
    )

    # ------------------------------------------------------------------
    # market_assignments  (depends on market_listings)
    # ------------------------------------------------------------------
    op.create_table(
        "market_assignments",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "listing_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("sales.market_listings.id"),
            nullable=False,
        ),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("buyer_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "assigned_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("payment_intent_id", sa.String(255), nullable=True),
        sa.Column("holder_name", sa.String(255), nullable=True),
        sa.Column("holder_dni", sa.String(50), nullable=True),
        sa.Column("state", sa.String(32), nullable=False, server_default="pending"),
        sa.CheckConstraint(
            "state IN ('pending', 'paid', 'expired', 'declined')",
            name="ck_market_assignments_state",
        ),
        schema="sales",
    )
    op.create_index(
        "ix_market_assignments_listing_id",
        "market_assignments",
        ["listing_id"],
        schema="sales",
    )
    op.create_index(
        "ix_market_assignments_buyer_user_id",
        "market_assignments",
        ["buyer_user_id"],
        schema="sales",
    )
    op.create_index(
        "ix_market_assignments_pending_expires",
        "market_assignments",
        ["expires_at"],
        schema="sales",
        postgresql_where=sa.text("state = 'pending'"),
    )


# drops the sales schema and its tables
def downgrade() -> None:
    # Drop in reverse dependency order (children before parents)

    op.drop_index(
        "ix_market_assignments_pending_expires", table_name="market_assignments", schema="sales"
    )
    op.drop_index(
        "ix_market_assignments_buyer_user_id", table_name="market_assignments", schema="sales"
    )
    op.drop_index(
        "ix_market_assignments_listing_id", table_name="market_assignments", schema="sales"
    )
    op.drop_table("market_assignments", schema="sales")

    op.drop_index(
        "ix_market_listings_expires_at_state", table_name="market_listings", schema="sales"
    )
    op.drop_index("ix_market_listings_seller_user_id", table_name="market_listings", schema="sales")
    op.drop_index("ix_market_listings_event_id_state", table_name="market_listings", schema="sales")
    op.drop_table("market_listings", schema="sales")

    op.execute("DROP INDEX IF EXISTS sales.uq_market_queue_entries_active_event_user")
    op.drop_index(
        "ix_market_queue_entries_user_id", table_name="market_queue_entries", schema="sales"
    )
    op.drop_index(
        "ix_market_queue_entries_event_id_active", table_name="market_queue_entries", schema="sales"
    )
    op.drop_table("market_queue_entries", schema="sales")

    op.drop_index(
        "ix_reservation_holders_reservation_id", table_name="reservation_holders", schema="sales"
    )
    op.drop_table("reservation_holders", schema="sales")

    op.execute("DROP TABLE IF EXISTS sales.fingerprint_context")
    op.execute("DROP TABLE IF EXISTS sales.user_age_context")
    op.execute("DROP TABLE IF EXISTS sales.ticket_type_inventory")
    op.execute("DROP TABLE IF EXISTS sales.event_context")
    op.execute("DROP TABLE IF EXISTS sales.reservations")

    op.execute("DROP SCHEMA IF EXISTS sales")
