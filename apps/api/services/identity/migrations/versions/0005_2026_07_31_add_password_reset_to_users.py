"""add password_reset columns to users

Revision ID: 0005_add_password_reset_to_users
Revises: 0004_add_totp_to_users
Create Date: 2026-07-31 00:00:00.000000

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005_add_password_reset_to_users"
down_revision: str | None = "0004_add_totp_to_users"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("password_reset_token", sa.String(255), nullable=True),
        schema="identity",
    )
    op.create_index(
        "ix_identity_users_password_reset_token",
        "users",
        ["password_reset_token"],
        schema="identity",
    )
    op.add_column(
        "users",
        sa.Column("password_reset_token_expires_at", sa.DateTime(timezone=True), nullable=True),
        schema="identity",
    )


def downgrade() -> None:
    op.drop_index("ix_identity_users_password_reset_token", "users", schema="identity")
    op.drop_column("users", "password_reset_token_expires_at", schema="identity")
    op.drop_column("users", "password_reset_token", schema="identity")
