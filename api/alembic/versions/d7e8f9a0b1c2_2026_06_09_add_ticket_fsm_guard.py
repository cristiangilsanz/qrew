"""2026_06_09_add_ticket_fsm_guard

Revision ID: d7e8f9a0b1c2
Revises: c6d7e8f9a0b1
Create Date: 2026-06-09 04:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d7e8f9a0b1c2"
down_revision: str | None = "c6d7e8f9a0b1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TRIGGER_FUNCTION = """
CREATE OR REPLACE FUNCTION tickets_state_transition_guard()
RETURNS trigger AS $$
DECLARE
    legal_pairs CONSTANT text[] := ARRAY[
        'reserved->issued',
        'reserved->cancelled',
        'issued->entry_pending',
        'issued->cancelled',
        'issued->frozen',
        'issued->flagged',
        'frozen->issued',
        'frozen->cancelled',
        'frozen->flagged',
        'entry_pending->used',
        'entry_pending->issued',
        'entry_pending->cancelled',
        'flagged->cancelled',
        'flagged->issued'
    ];
BEGIN
    IF OLD.state IS DISTINCT FROM NEW.state THEN
        IF OLD.state IN ('used', 'cancelled') THEN
            RAISE EXCEPTION 'ticket %% is in terminal state %%', OLD.id, OLD.state
                USING ERRCODE = 'check_violation';
        END IF;
        IF NOT (OLD.state || '->' || NEW.state = ANY(legal_pairs)) THEN
            RAISE EXCEPTION 'illegal ticket transition %% -> %% on ticket %%',
                OLD.state, NEW.state, OLD.id
                USING ERRCODE = 'check_violation';
        END IF;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
"""


def upgrade() -> None:
    op.add_column(
        "tickets",
        sa.Column("state_updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.execute(_TRIGGER_FUNCTION)
    op.execute("DROP TRIGGER IF EXISTS tickets_state_guard ON tickets")
    op.execute(
        "CREATE TRIGGER tickets_state_guard BEFORE UPDATE ON tickets "
        "FOR EACH ROW EXECUTE FUNCTION tickets_state_transition_guard()"
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS tickets_state_guard ON tickets")
    op.execute("DROP FUNCTION IF EXISTS tickets_state_transition_guard()")
    op.drop_column("tickets", "state_updated_at")
