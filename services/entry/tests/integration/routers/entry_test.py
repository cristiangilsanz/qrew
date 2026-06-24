import uuid
from unittest.mock import patch

import pytest

from tests.integration.conftest import (
    _noop_redlock,
    _noop_ticketing_use,
    make_access_token,
    make_scanner_token,
    make_ticket_qr_jwt,
    seed_event,
    seed_org_member,
    seed_scanner,
    seed_ticket_context,
    seed_user,
)

pytestmark = [pytest.mark.integration, pytest.mark.asyncio(loop_scope="session")]


@pytest.fixture
async def base_ids():
    return {
        "event_id": uuid.uuid4(),
        "venue_id": uuid.uuid4(),
        "owner_user_id": uuid.uuid4(),
    }


# ---------------------------------------------------------------------------
# POST /v1/entry/validate
# ---------------------------------------------------------------------------


async def test_validate_entry_success(client, db, fake_redis, base_ids):
    event_id = base_ids["event_id"]
    venue_id = base_ids["venue_id"]
    owner_user_id = base_ids["owner_user_id"]

    user = await seed_user(db)
    scanner = await seed_scanner(db, created_by=user.id, venue_id=venue_id)
    tc = await seed_ticket_context(
        db, event_id=event_id, venue_id=venue_id, owner_user_id=owner_user_id
    )

    scanner_token = make_scanner_token(scanner.id, venue_id, event_id)
    ticket_jwt = make_ticket_qr_jwt(tc.ticket_id, event_id, venue_id)

    with (
        patch(
            "com.qode.qrew.v1.entry.services.application.entry.entry.redlock",
            _noop_redlock,
        ),
        patch(
            "com.qode.qrew.v1.entry.services.application.entry.entry._call_ticketing_use",
            _noop_ticketing_use,
        ),
    ):
        response = await client.post(
            "/v1/entry/validate",
            json={"ticket_jwt": ticket_jwt},
            headers={"Authorization": f"Bearer {scanner_token}"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["allowed"] is True
    assert data["reason"] is None
    assert data["ticket_id"] == str(tc.ticket_id)


async def test_validate_entry_no_auth(client):
    response = await client.post(
        "/v1/entry/validate",
        json={"ticket_jwt": "dummy"},
    )
    assert response.status_code == 401


async def test_validate_entry_replay(client, db, fake_redis, base_ids):
    event_id = base_ids["event_id"]
    venue_id = base_ids["venue_id"]
    owner_user_id = base_ids["owner_user_id"]

    user = await seed_user(db)
    scanner = await seed_scanner(db, created_by=user.id, venue_id=venue_id)
    tc = await seed_ticket_context(
        db, event_id=event_id, venue_id=venue_id, owner_user_id=owner_user_id
    )

    shared_jti = str(uuid.uuid4())
    scanner_token = make_scanner_token(scanner.id, venue_id, event_id)
    ticket_jwt = make_ticket_qr_jwt(tc.ticket_id, event_id, venue_id, jti=shared_jti)

    with (
        patch(
            "com.qode.qrew.v1.entry.services.application.entry.entry.redlock",
            _noop_redlock,
        ),
        patch(
            "com.qode.qrew.v1.entry.services.application.entry.entry._call_ticketing_use",
            _noop_ticketing_use,
        ),
    ):
        r1 = await client.post(
            "/v1/entry/validate",
            json={"ticket_jwt": ticket_jwt},
            headers={"Authorization": f"Bearer {scanner_token}"},
        )
        r2 = await client.post(
            "/v1/entry/validate",
            json={"ticket_jwt": ticket_jwt},
            headers={"Authorization": f"Bearer {scanner_token}"},
        )

    assert r1.json()["allowed"] is True
    assert r2.json()["allowed"] is False
    assert r2.json()["reason"] == "replay"


async def test_validate_entry_ticket_used_state(client, db, fake_redis, base_ids):
    event_id = base_ids["event_id"]
    venue_id = base_ids["venue_id"]
    owner_user_id = base_ids["owner_user_id"]

    user = await seed_user(db)
    scanner = await seed_scanner(db, created_by=user.id, venue_id=venue_id)
    tc = await seed_ticket_context(
        db,
        event_id=event_id,
        venue_id=venue_id,
        owner_user_id=owner_user_id,
        state="used",
    )

    scanner_token = make_scanner_token(scanner.id, venue_id, event_id)
    ticket_jwt = make_ticket_qr_jwt(tc.ticket_id, event_id, venue_id)

    with (
        patch(
            "com.qode.qrew.v1.entry.services.application.entry.entry.redlock",
            _noop_redlock,
        ),
        patch(
            "com.qode.qrew.v1.entry.services.application.entry.entry._call_ticketing_use",
            _noop_ticketing_use,
        ),
    ):
        response = await client.post(
            "/v1/entry/validate",
            json={"ticket_jwt": ticket_jwt},
            headers={"Authorization": f"Bearer {scanner_token}"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["allowed"] is False
    assert data["reason"] == "state"


# ---------------------------------------------------------------------------
# GET /v1/events/{event_id}/entry-stats
# ---------------------------------------------------------------------------


async def test_entry_stats_success(client, db):
    org_id = uuid.uuid4()
    user = await seed_user(db)
    event = await seed_event(db, organisation_id=org_id)
    await seed_org_member(db, organisation_id=org_id, user_id=user.id)

    token = make_access_token(user.id)
    response = await client.get(
        f"/v1/events/{event.id}/entry-stats",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["event_id"] == str(event.id)
    assert data["total_issued"] == 0


async def test_entry_stats_not_member(client, db):
    org_id = uuid.uuid4()
    user = await seed_user(db)
    other_user = await seed_user(db)
    event = await seed_event(db, organisation_id=org_id)
    await seed_org_member(db, organisation_id=org_id, user_id=other_user.id)

    token = make_access_token(user.id)
    response = await client.get(
        f"/v1/events/{event.id}/entry-stats",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403


async def test_entry_stats_no_auth(client):
    response = await client.get(f"/v1/events/{uuid.uuid4()}/entry-stats")
    assert response.status_code == 401


async def test_entry_stats_event_not_found(client, db):
    user = await seed_user(db)
    token = make_access_token(user.id)
    response = await client.get(
        f"/v1/events/{uuid.uuid4()}/entry-stats",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 404
