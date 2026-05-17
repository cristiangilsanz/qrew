"""add last_used_at, name, and cascade to passkey_credentials

Revision ID: a1b2c3d4e5f6
Revises: 3abe87e2c49f
Create Date: 2026-05-17 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a1b2c3d4e5f6"
down_revision: str | None = "3abe87e2c49f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "passkey_credentials",
        sa.Column("name", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "passkey_credentials",
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.drop_constraint(
        "passkey_credentials_user_id_fkey",
        "passkey_credentials",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "passkey_credentials_user_id_fkey",
        "passkey_credentials",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    op.drop_constraint(
        "passkey_credentials_user_id_fkey",
        "passkey_credentials",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "passkey_credentials_user_id_fkey",
        "passkey_credentials",
        "users",
        ["user_id"],
        ["id"],
    )
    op.drop_column("passkey_credentials", "last_used_at")
    op.drop_column("passkey_credentials", "name")
