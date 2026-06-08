"""2026_06_08_add_venues_table

Revision ID: c0d1e2f3a4b5
Revises: b9c0d1e2f3a4
Create Date: 2026-06-08 01:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "c0d1e2f3a4b5"
down_revision: str | None = "b9c0d1e2f3a4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "venues",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("address_line", sa.String(length=256), nullable=False),
        sa.Column("city", sa.String(length=96), nullable=False),
        sa.Column("country", sa.String(length=2), nullable=False),
        sa.Column("latitude", sa.Numeric(9, 6), nullable=False),
        sa.Column("longitude", sa.Numeric(9, 6), nullable=False),
        sa.Column(
            "geofence_radius_m",
            sa.Integer,
            nullable=False,
            server_default="200",
        ),
        sa.Column("timezone", sa.String(length=64), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
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
        sa.CheckConstraint(
            "latitude >= -90 AND latitude <= 90", name="ck_venues_latitude"
        ),
        sa.CheckConstraint(
            "longitude >= -180 AND longitude <= 180", name="ck_venues_longitude"
        ),
        sa.CheckConstraint(
            "geofence_radius_m >= 50 AND geofence_radius_m <= 5000",
            name="ck_venues_geofence_radius",
        ),
    )
    op.create_index("ix_venues_city_country", "venues", ["city", "country"])


def downgrade() -> None:
    op.drop_index("ix_venues_city_country", table_name="venues")
    op.drop_table("venues")
