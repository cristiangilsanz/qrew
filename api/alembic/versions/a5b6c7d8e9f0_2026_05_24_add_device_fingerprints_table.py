"""2026_05_24_add_device_fingerprints_table

Revision ID: a5b6c7d8e9f0
Revises: f4a5b6c7d8e9
Create Date: 2026-05-24 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a5b6c7d8e9f0"
down_revision: str | None = "f4a5b6c7d8e9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "device_fingerprints",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("fingerprint_hash", sa.String(255), nullable=False),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column(
            "seen_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("account_count_at_seen", sa.Integer(), nullable=False, default=1),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id", "fingerprint_hash", name="uq_device_fingerprints_user_hash"
        ),
    )
    op.create_index(
        "ix_device_fingerprints_user_id", "device_fingerprints", ["user_id"]
    )
    op.create_index(
        "ix_device_fingerprints_fingerprint_hash",
        "device_fingerprints",
        ["fingerprint_hash"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_device_fingerprints_fingerprint_hash", table_name="device_fingerprints"
    )
    op.drop_index("ix_device_fingerprints_user_id", table_name="device_fingerprints")
    op.drop_table("device_fingerprints")
