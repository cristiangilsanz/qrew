"""add totp columns to users

Revision ID: 0004_add_totp_to_users
Revises: 0003_add_outbox_table
Create Date: 2026-07-29 00:00:00.000000

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004_add_totp_to_users"
down_revision: str | None = "0003_add_outbox_table"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("totp_secret_ciphertext", sa.LargeBinary(), nullable=True),
        schema="identity",
    )
    op.add_column(
        "users",
        sa.Column(
            "totp_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        schema="identity",
    )
    op.add_column(
        "users",
        sa.Column("totp_backup_codes_json", sa.Text(), nullable=True),
        schema="identity",
    )


def downgrade() -> None:
    op.drop_column("users", "totp_backup_codes_json", schema="identity")
    op.drop_column("users", "totp_enabled", schema="identity")
    op.drop_column("users", "totp_secret_ciphertext", schema="identity")
