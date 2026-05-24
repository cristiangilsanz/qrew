"""2026_05_24_add_pending_email_to_users

Revision ID: e3f4a5b6c7d8
Revises: d2e3f4a5b6c7
Create Date: 2026-05-24 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e3f4a5b6c7d8"
down_revision: str | None = "d2e3f4a5b6c7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("pending_email", sa.String(255), nullable=True))
    op.add_column(
        "users",
        sa.Column("pending_email_verification_token", sa.String(255), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column(
            "pending_email_token_expires_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_users_pending_email_verification_token",
        "users",
        ["pending_email_verification_token"],
    )


def downgrade() -> None:
    op.drop_index("ix_users_pending_email_verification_token", table_name="users")
    op.drop_column("users", "pending_email_token_expires_at")
    op.drop_column("users", "pending_email_verification_token")
    op.drop_column("users", "pending_email")
