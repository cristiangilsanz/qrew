"""add market queue, listings, and assignments tables

Revision ID: 0004_sales_market_tables
Revises: 0003_sales_reservation_holders
Create Date: 2026-07-23 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004_sales_market_tables"
down_revision: Union[str, None] = "0003_sales_reservation_holders"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
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
        sa.UniqueConstraint("event_id", "user_id", name="uq_market_queue_entries_event_user"),
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
        sa.Column(
            "state",
            sa.String(32),
            nullable=False,
            server_default="available",
        ),
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
        sa.Column(
            "state",
            sa.String(32),
            nullable=False,
            server_default="pending",
        ),
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


def downgrade() -> None:
    op.drop_index("ix_market_assignments_pending_expires", table_name="market_assignments", schema="sales")
    op.drop_index("ix_market_assignments_buyer_user_id", table_name="market_assignments", schema="sales")
    op.drop_index("ix_market_assignments_listing_id", table_name="market_assignments", schema="sales")
    op.drop_table("market_assignments", schema="sales")

    op.drop_index("ix_market_listings_expires_at_state", table_name="market_listings", schema="sales")
    op.drop_index("ix_market_listings_seller_user_id", table_name="market_listings", schema="sales")
    op.drop_index("ix_market_listings_event_id_state", table_name="market_listings", schema="sales")
    op.drop_table("market_listings", schema="sales")

    op.drop_index("ix_market_queue_entries_user_id", table_name="market_queue_entries", schema="sales")
    op.drop_index("ix_market_queue_entries_event_id_active", table_name="market_queue_entries", schema="sales")
    op.drop_table("market_queue_entries", schema="sales")
