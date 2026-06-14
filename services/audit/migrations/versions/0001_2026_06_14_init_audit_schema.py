"""init audit schema (stub — table pre-exists from monolith migration)

Revision ID: a1b2c3d4e5f6
Revises:
Create Date: 2026-06-14 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS audit")

    op.execute("""
        CREATE TABLE IF NOT EXISTS audit.audit_events (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            actor_id UUID,
            action VARCHAR(64) NOT NULL,
            entity_type VARCHAR(64),
            entity_id VARCHAR(255),
            ip_address VARCHAR(45),
            device_fingerprint_hash VARCHAR(255),
            user_agent TEXT,
            payload JSONB NOT NULL DEFAULT '{}',
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            prev_hash BYTEA,
            hash BYTEA NOT NULL
        )
    """)

    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_audit_events_actor_id
            ON audit.audit_events (actor_id)
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_audit_events_action
            ON audit.audit_events (action)
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_audit_events_created_at
            ON audit.audit_events (created_at)
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS audit.audit_events")
    op.execute("DROP SCHEMA IF EXISTS audit")
