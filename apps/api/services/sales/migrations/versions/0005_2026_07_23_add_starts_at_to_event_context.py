"""add starts_at to event_context

Revision ID: 0005_sales_event_context_starts_at
Revises: 0004_sales_market_tables
Create Date: 2026-07-23 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "0005_sales_starts_at"
down_revision = "0004_sales_market_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "event_context",
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=True),
        schema="sales",
    )


def downgrade() -> None:
    op.drop_column("event_context", "starts_at", schema="sales")
