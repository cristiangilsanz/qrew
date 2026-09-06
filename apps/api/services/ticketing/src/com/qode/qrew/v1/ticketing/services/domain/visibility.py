# decides how long a ticket stays in the listing once its event is over
from datetime import datetime, timedelta

# a ticket keeps showing for a day past the end of its event, then it drops out
PAST_EVENT_GRACE = timedelta(days=1)


# the instant an event must have ended before for its tickets to leave the listing
def past_event_cutoff(now: datetime) -> datetime:
    return now - PAST_EVENT_GRACE


# reports whether a ticket for an event ending then still belongs in the listing,
# keeping the ticket whenever the projection has no end time to judge it by
def is_listed(ends_at: datetime | None, now: datetime) -> bool:
    if ends_at is None:
        return True
    return ends_at > past_event_cutoff(now)
