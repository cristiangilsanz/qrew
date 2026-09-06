# tests how long a ticket stays in the listing after its event ends
from datetime import UTC, datetime, timedelta

from com.qode.qrew.v1.ticketing.services.domain.visibility import (
    PAST_EVENT_GRACE,
    is_listed,
    past_event_cutoff,
)

NOW = datetime(2026, 6, 1, 12, 0, tzinfo=UTC)


class TestPastEventCutoff:
    # verifies that the cutoff sits one day behind the present
    def test_cutoff_is_a_day_back(self) -> None:
        assert past_event_cutoff(NOW) == NOW - timedelta(days=1)
        assert PAST_EVENT_GRACE == timedelta(days=1)


class TestIsListed:
    # verifies that an event still to come is listed
    def test_future_event_is_listed(self) -> None:
        assert is_listed(NOW + timedelta(days=7), NOW) is True

    # verifies that an event that just ended is still listed
    def test_event_that_just_ended_is_listed(self) -> None:
        assert is_listed(NOW - timedelta(minutes=1), NOW) is True

    # verifies that the whole grace day keeps the ticket in the listing
    def test_within_the_grace_day_is_listed(self) -> None:
        assert is_listed(NOW - timedelta(hours=23, minutes=59), NOW) is True

    # verifies that an event over for more than a day drops out
    def test_event_over_a_day_ago_is_hidden(self) -> None:
        assert is_listed(NOW - timedelta(days=1, seconds=1), NOW) is False

    # verifies that an old event drops out
    def test_long_past_event_is_hidden(self) -> None:
        assert is_listed(NOW - timedelta(days=400), NOW) is False

    # verifies that the boundary itself drops out, so the grace day is closed
    def test_exactly_on_the_cutoff_is_hidden(self) -> None:
        assert is_listed(past_event_cutoff(NOW), NOW) is False

    # verifies that a ticket the projection cannot date is kept
    def test_unknown_end_is_listed(self) -> None:
        assert is_listed(None, NOW) is True
