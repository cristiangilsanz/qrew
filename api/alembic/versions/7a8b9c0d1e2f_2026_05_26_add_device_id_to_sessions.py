"""2026_05_26_add_device_id_to_sessions

Revision ID: 7a8b9c0d1e2f
Revises: 6f9d4a5d9ce4
Create Date: 2026-05-26 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "7a8b9c0d1e2f"
down_revision: str | None = "6f9d4a5d9ce4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "sessions",
        sa.Column("device_id", sa.UUID(), nullable=True),
    )
    op.create_foreign_key(
        "fk_sessions_device_id_devices",
        "sessions",
        "devices",
        ["device_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        op.f("ix_sessions_device_id"),
        "sessions",
        ["device_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_sessions_device_id"), table_name="sessions")
    op.drop_constraint("fk_sessions_device_id_devices", "sessions", type_="foreignkey")
    op.drop_column("sessions", "device_id")
