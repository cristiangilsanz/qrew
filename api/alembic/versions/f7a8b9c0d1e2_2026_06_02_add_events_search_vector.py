"""2026_06_02_add_events_search_vector

Revision ID: f7a8b9c0d1e2
Revises: e6f7a8b9c0d1
Create Date: 2026-06-02 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from com.qode.qrew.v1.service.core.search import create_trigger_sql, drop_trigger_sql
from com.qode.qrew.v1.service.search.events import EVENTS_SEARCH_CONFIG

revision: str = "f7a8b9c0d1e2"
down_revision: str | None = "e6f7a8b9c0d1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if EVENTS_SEARCH_CONFIG.table not in inspector.get_table_names():
        return
    op.add_column(
        EVENTS_SEARCH_CONFIG.table,
        sa.Column(
            EVENTS_SEARCH_CONFIG.vector_column,
            postgresql.TSVECTOR,
            nullable=True,
        ),
    )
    op.create_index(
        EVENTS_SEARCH_CONFIG.index_name,
        EVENTS_SEARCH_CONFIG.table,
        [EVENTS_SEARCH_CONFIG.vector_column],
        postgresql_using="gin",
    )
    for statement in create_trigger_sql(EVENTS_SEARCH_CONFIG):
        op.execute(statement)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if EVENTS_SEARCH_CONFIG.table not in inspector.get_table_names():
        return
    for statement in drop_trigger_sql(EVENTS_SEARCH_CONFIG):
        op.execute(statement)
    op.drop_index(
        EVENTS_SEARCH_CONFIG.index_name, table_name=EVENTS_SEARCH_CONFIG.table
    )
    op.drop_column(EVENTS_SEARCH_CONFIG.table, EVENTS_SEARCH_CONFIG.vector_column)
