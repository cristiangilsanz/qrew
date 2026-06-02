"""2026_06_02_add_notifications_table

Revision ID: e6f7a8b9c0d1
Revises: d5e6f7a8b9c0
Create Date: 2026-06-02 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "e6f7a8b9c0d1"
down_revision: str | None = "d5e6f7a8b9c0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "notifications",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "channel",
            sa.Enum("email", "sms", name="notification_channel"),
            nullable=False,
        ),
        sa.Column("template_key", sa.String(length=64), nullable=False),
        sa.Column("destination_ciphertext", sa.LargeBinary, nullable=False),
        sa.Column(
            "payload",
            postgresql.JSONB,
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "status",
            sa.Enum("pending", "sent", "failed", name="notification_status"),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("error", sa.Text, nullable=True),
        sa.Column(
            "attempt_count",
            sa.Integer,
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_notifications_user_id_created_at",
        "notifications",
        ["user_id", sa.text("created_at DESC")],
    )
    op.create_index("ix_notifications_status", "notifications", ["status"])
    op.create_index("ix_notifications_template_key", "notifications", ["template_key"])


def downgrade() -> None:
    op.drop_index("ix_notifications_template_key", table_name="notifications")
    op.drop_index("ix_notifications_status", table_name="notifications")
    op.drop_index("ix_notifications_user_id_created_at", table_name="notifications")
    op.drop_table("notifications")
    op.execute("DROP TYPE notification_status")
    op.execute("DROP TYPE notification_channel")
