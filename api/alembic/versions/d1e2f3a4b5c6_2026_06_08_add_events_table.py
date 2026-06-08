"""2026_06_08_add_events_table

Revision ID: d1e2f3a4b5c6
Revises: c0d1e2f3a4b5
Create Date: 2026-06-08 02:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from com.qode.qrew.v1.service.core.search import create_trigger_sql, drop_trigger_sql
from com.qode.qrew.v1.service.search.events import EVENTS_SEARCH_CONFIG

revision: str = "d1e2f3a4b5c6"
down_revision: str | None = "c0d1e2f3a4b5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "events",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "organisation_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organisations.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "venue_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("venues.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sale_starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sale_ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "max_tickets_per_user",
            sa.Integer,
            nullable=False,
            server_default="4",
        ),
        sa.Column(
            "status",
            sa.String(16),
            nullable=False,
            server_default="draft",
        ),
        sa.Column("organiser_name", sa.String(128), nullable=False),
        sa.Column("venue_city", sa.String(96), nullable=False),
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
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("starts_at < ends_at", name="ck_events_time_window"),
        sa.CheckConstraint(
            "sale_starts_at < sale_ends_at", name="ck_events_sale_window"
        ),
        sa.CheckConstraint(
            "sale_ends_at <= starts_at", name="ck_events_sale_before_start"
        ),
        sa.CheckConstraint(
            "max_tickets_per_user >= 1 AND max_tickets_per_user <= 20",
            name="ck_events_max_tickets_per_user",
        ),
        sa.CheckConstraint(
            "status IN ('draft', 'published', 'cancelled')",
            name="ck_events_status",
        ),
    )
    op.create_index("ix_events_organisation_id", "events", ["organisation_id"])
    op.create_index("ix_events_venue_id", "events", ["venue_id"])
    op.create_index("ix_events_status_starts_at", "events", ["status", "starts_at"])
    op.add_column(
        EVENTS_SEARCH_CONFIG.table,
        sa.Column(
            EVENTS_SEARCH_CONFIG.vector_column,
            postgresql.TSVECTOR,
            nullable=True,
        ),
    )
    op.create_index(
        EVENTS_SEARCH_CONFIG.index_name,
        EVENTS_SEARCH_CONFIG.table,
        [EVENTS_SEARCH_CONFIG.vector_column],
        postgresql_using="gin",
    )
    op.execute(create_trigger_sql(EVENTS_SEARCH_CONFIG))


def downgrade() -> None:
    op.execute(drop_trigger_sql(EVENTS_SEARCH_CONFIG))
    op.drop_index("ix_events_status_starts_at", table_name="events")
    op.drop_index("ix_events_venue_id", table_name="events")
    op.drop_index("ix_events_organisation_id", table_name="events")
    op.drop_index(
        EVENTS_SEARCH_CONFIG.index_name, table_name=EVENTS_SEARCH_CONFIG.table
    )
    op.drop_table("events")
