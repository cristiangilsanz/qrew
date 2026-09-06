# tests the query behind the ticket listing
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.dialects import postgresql

from com.qode.qrew.v1.ticketing.repositories.ticket import list_by_user_stmt

NOW = datetime(2026, 6, 1, 12, 0, tzinfo=UTC)
CUTOFF = NOW - timedelta(days=1)


# renders the statement the way the database receives it
def _sql(user_id: uuid.UUID) -> str:
    compiled = list_by_user_stmt(user_id, CUTOFF).compile(dialect=postgresql.dialect())
    return str(compiled)


class TestListByUserStmt:
    # verifies that the listing reads the event end time from the local projection
    def test_joins_the_event_projection(self) -> None:
        sql = _sql(uuid.uuid4())
        assert "LEFT OUTER JOIN ticketing.event_venue_context" in sql
        assert "ticketing.event_venue_context.event_id = ticketing.tickets.event_id" in sql

    # verifies that the listing is still scoped to the caller
    def test_scopes_to_the_owner(self) -> None:
        assert "ticketing.tickets.owner_user_id = " in _sql(uuid.uuid4())

    # verifies that an event long over is left out, while an undated one is kept
    def test_drops_long_past_events_and_keeps_undated_ones(self) -> None:
        sql = _sql(uuid.uuid4())
        assert "ticketing.event_venue_context.ends_at IS NULL" in sql
        assert "ticketing.event_venue_context.ends_at > " in sql
        assert " OR " in sql

    # verifies that the cutoff travels as a bound parameter, never inlined
    def test_cutoff_is_bound(self) -> None:
        stmt = list_by_user_stmt(uuid.uuid4(), CUTOFF)
        params = stmt.compile(dialect=postgresql.dialect()).params
        assert CUTOFF in params.values()

    # verifies that the newest ticket still comes first
    def test_orders_newest_first(self) -> None:
        assert "ORDER BY ticketing.tickets.created_at DESC" in _sql(uuid.uuid4())

    # verifies that nothing is deleted, the listing only reads
    def test_is_a_read_only_select(self) -> None:
        assert _sql(uuid.uuid4()).lstrip().startswith("SELECT")
