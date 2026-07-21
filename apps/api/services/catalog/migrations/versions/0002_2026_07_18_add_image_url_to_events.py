"""add image_url to events

Revision ID: 0002_add_image_url
Revises: 0001_init
Create Date: 2026-07-18
"""

from alembic import op

revision = "0002_add_image_url"
down_revision = "0001_catalog_init"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE catalog.events ADD COLUMN IF NOT EXISTS image_url VARCHAR(500)")


def downgrade() -> None:
    op.execute("ALTER TABLE catalog.events DROP COLUMN IF EXISTS image_url")
