# tests that the listing leaves out the tickets of events long over
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import text

pytestmark = [pytest.mark.integration, pytest.mark.asyncio(loop_scope="session")]

NOW = datetime.now(UTC)


# leaves an issued ticket for the given event in the database
async def _seed_ticket(session_factory, *, user_id: uuid.UUID, event_id: uuid.UUID) -> uuid.UUID:
    ticket_id = uuid.uuid4()
    async with session_factory() as session, session.begin():
        await session.execute(
            text("""
                INSERT INTO ticketing.tickets
                    (id, reservation_id, event_id, ticket_type_id, owner_user_id, state)
                VALUES (:id, :res_id, :ev_id, :tt_id, :owner_id, 'issued')
            """),
            {
                "id": ticket_id,
                "res_id": uuid.uuid4(),
                "ev_id": event_id,
                "tt_id": uuid.uuid4(),
                "owner_id": user_id,
            },
        )
    return ticket_id


# leaves the local projection of an event that ends at the given instant
async def _seed_event(session_factory, *, event_id: uuid.UUID, ends_at: datetime | None) -> None:
    async with session_factory() as session, session.begin():
        await session.execute(
            text("""
                INSERT INTO ticketing.event_venue_context
                    (event_id, venue_id, event_status, starts_at, ends_at)
                VALUES (:event_id, :venue_id, 'published', :starts_at, :ends_at)
            """),
            {
                "event_id": event_id,
                "venue_id": uuid.uuid4(),
                "starts_at": ends_at - timedelta(hours=3) if ends_at else None,
                "ends_at": ends_at,
            },
        )


# verifies that only the tickets of events not long over reach the listing
async def test_listing_hides_events_over_a_day_ago(client, test_session_factory, make_auth_headers):
    user_id = uuid.uuid4()
    upcoming, just_over, long_over, undated, unprojected = (uuid.uuid4() for _ in range(5))

    await _seed_event(test_session_factory, event_id=upcoming, ends_at=NOW + timedelta(days=5))
    await _seed_event(test_session_factory, event_id=just_over, ends_at=NOW - timedelta(hours=2))
    await _seed_event(test_session_factory, event_id=long_over, ends_at=NOW - timedelta(days=30))
    await _seed_event(test_session_factory, event_id=undated, ends_at=None)

    ids = {}
    for name, event_id in (
        ("upcoming", upcoming),
        ("just_over", just_over),
        ("long_over", long_over),
        ("undated", undated),
        ("unprojected", unprojected),
    ):
        ids[name] = await _seed_ticket(test_session_factory, user_id=user_id, event_id=event_id)

    headers = make_auth_headers(user_id)
    response = await client.get("/v1/tickets", headers=headers)

    assert response.status_code == 200
    listed = {t["id"] for t in response.json()}
    assert str(ids["upcoming"]) in listed
    assert str(ids["just_over"]) in listed
    assert str(ids["undated"]) in listed
    assert str(ids["unprojected"]) in listed
    assert str(ids["long_over"]) not in listed


# verifies that a hidden ticket is still readable by its identifier and still stored
async def test_hidden_ticket_is_kept_and_readable(client, test_session_factory, make_auth_headers):
    user_id = uuid.uuid4()
    event_id = uuid.uuid4()
    await _seed_event(test_session_factory, event_id=event_id, ends_at=NOW - timedelta(days=90))
    ticket_id = await _seed_ticket(test_session_factory, user_id=user_id, event_id=event_id)

    headers = make_auth_headers(user_id)
    listing = await client.get("/v1/tickets", headers=headers)
    assert str(ticket_id) not in {t["id"] for t in listing.json()}

    detail = await client.get(f"/v1/tickets/{ticket_id}", headers=headers)
    assert detail.status_code == 200
    assert detail.json()["id"] == str(ticket_id)

    async with test_session_factory() as session:
        rows = await session.execute(
            text("SELECT count(*) FROM ticketing.tickets WHERE id = :id"), {"id": ticket_id}
        )
        assert rows.scalar_one() == 1
