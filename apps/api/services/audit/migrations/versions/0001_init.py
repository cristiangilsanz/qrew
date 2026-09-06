"""init audit schema

Revision ID: 0001_audit_init
Revises:
Create Date: 2026-06-14 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_audit_init"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# creates the audit schema and its tables
def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS audit")

    op.create_table(
        "audit_events",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("action", sa.VARCHAR(length=64), nullable=False),
        sa.Column("entity_type", sa.VARCHAR(length=64), nullable=True),
        sa.Column("entity_id", sa.VARCHAR(length=255), nullable=True),
        sa.Column("ip_address", sa.VARCHAR(length=45), nullable=True),
        sa.Column("device_fingerprint_hash", sa.VARCHAR(length=255), nullable=True),
        sa.Column("user_agent", sa.TEXT(), nullable=True),
        sa.Column(
            "payload",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("prev_hash", sa.LargeBinary(), nullable=True),
        sa.Column("hash", sa.LargeBinary(), nullable=False),
        schema="audit",
    )

    op.create_index(
        "ix_audit_events_actor_id",
        "audit_events",
        ["actor_id"],
        schema="audit",
    )
    op.create_index(
        "ix_audit_events_action",
        "audit_events",
        ["action"],
        schema="audit",
    )
    op.create_index(
        "ix_audit_events_created_at",
        "audit_events",
        ["created_at"],
        schema="audit",
    )


# drops the audit schema and its tables
def downgrade() -> None:
    op.drop_index("ix_audit_events_created_at", table_name="audit_events", schema="audit")
    op.drop_index("ix_audit_events_action", table_name="audit_events", schema="audit")
    op.drop_index("ix_audit_events_actor_id", table_name="audit_events", schema="audit")
    op.drop_table("audit_events", schema="audit")
    op.execute("DROP SCHEMA IF EXISTS audit")
