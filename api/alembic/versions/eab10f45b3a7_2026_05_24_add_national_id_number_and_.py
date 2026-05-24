"""2026_05_24_add_national_id_number_and_unique_constraint_to_users

Revision ID: eab10f45b3a7
Revises: a5b6c7d8e9f0
Create Date: 2026-05-24 20:38:28.659899

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "eab10f45b3a7"
down_revision: str | None = "a5b6c7d8e9f0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("national_id_number", sa.Text(), nullable=True))
    op.create_index(
        op.f("ix_users_national_id_hash"),
        "users",
        ["national_id_hash"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_users_national_id_hash"), table_name="users")
    op.drop_column("users", "national_id_number")
