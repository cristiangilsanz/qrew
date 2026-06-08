"""2026_06_08_add_ticket_types_table

Revision ID: e2f3a4b5c6d7
Revises: d1e2f3a4b5c6
Create Date: 2026-06-08 03:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "e2f3a4b5c6d7"
down_revision: str | None = "d1e2f3a4b5c6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ticket_types",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "event_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("events.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("name", sa.String(32), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("capacity", sa.Integer, nullable=False),
        sa.Column("reserved_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("price_cents", sa.Integer, nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("position", sa.Integer, nullable=False, server_default="0"),
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
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("event_id", "name", name="uq_ticket_types_event_id_name"),
        sa.CheckConstraint(
            "capacity >= 1 AND capacity <= 100000",
            name="ck_ticket_types_capacity",
        ),
        sa.CheckConstraint(
            "reserved_count >= 0 AND reserved_count <= capacity",
            name="ck_ticket_types_reserved_count",
        ),
        sa.CheckConstraint(
            "price_cents >= 0 AND price_cents <= 10000000",
            name="ck_ticket_types_price_cents",
        ),
    )
    op.create_index("ix_ticket_types_event_id", "ticket_types", ["event_id"])


def downgrade() -> None:
    op.drop_index("ix_ticket_types_event_id", table_name="ticket_types")
    op.drop_table("ticket_types")
