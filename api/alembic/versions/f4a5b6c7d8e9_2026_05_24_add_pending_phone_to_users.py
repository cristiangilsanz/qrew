"""2026_05_24_add_pending_phone_to_users

Revision ID: f4a5b6c7d8e9
Revises: e3f4a5b6c7d8
Create Date: 2026-05-24 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "f4a5b6c7d8e9"
down_revision: str | None = "e3f4a5b6c7d8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users", sa.Column("pending_phone_number", sa.String(20), nullable=True)
    )
    op.add_column("users", sa.Column("pending_phone_otp", sa.String(10), nullable=True))
    op.add_column(
        "users",
        sa.Column(
            "pending_phone_otp_expires_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "pending_phone_otp_expires_at")
    op.drop_column("users", "pending_phone_otp")
    op.drop_column("users", "pending_phone_number")
