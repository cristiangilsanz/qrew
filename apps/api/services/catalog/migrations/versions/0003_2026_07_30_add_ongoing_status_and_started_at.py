"""add ongoing status and started_at to events

Revision ID: 0003_add_ongoing_status
Revises: 0002_add_image_url
Create Date: 2026-07-30
"""

from alembic import op

revision = "0003_add_ongoing_status"
down_revision = "0002_add_image_url"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE catalog.events ADD COLUMN IF NOT EXISTS started_at TIMESTAMPTZ"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE catalog.events DROP COLUMN IF EXISTS started_at")
