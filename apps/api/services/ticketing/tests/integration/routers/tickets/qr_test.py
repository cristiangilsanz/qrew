import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import text

pytestmark = [pytest.mark.integration, pytest.mark.asyncio(loop_scope="session")]


async def _seed_qr_data(
    session_factory,
    *,
    user_id: uuid.UUID,
    device_id: uuid.UUID,
    ticket_state: str = "issued",
) -> uuid.UUID:
    """Seed a ticket + event_venue_context + device_context for gate evaluation."""
    ticket_id = uuid.uuid4()
    event_id = uuid.uuid4()
    now = datetime.now(UTC)

    async with session_factory() as session, session.begin():
        await session.execute(
            text("""
                INSERT INTO ticketing.tickets
                    (id, reservation_id, event_id, ticket_type_id, owner_user_id, bound_device_id, state)
                VALUES (:id, :res_id, :ev_id, :tt_id, :owner_id, :device_id, :state)
            """),
            {
                "id": ticket_id,
                "res_id": uuid.uuid4(),
                "ev_id": event_id,
                "tt_id": uuid.uuid4(),
                "owner_id": user_id,
                "device_id": device_id,
                "state": ticket_state,
            },
        )
        await session.execute(
            text("""
                INSERT INTO ticketing.event_venue_context
                    (event_id, venue_id, event_status, latitude, longitude, geofence_radius_m, timezone)
                VALUES (:event_id, :venue_id, 'active', 0.0, 0.0, 9999999, 'UTC')
            """),
            {"event_id": event_id, "venue_id": uuid.uuid4()},
        )
        await session.execute(
            text("""
                INSERT INTO ticketing.device_context
                    (device_id, user_id, attested_at, revoked_at)
                VALUES (:device_id, :user_id, :attested_at, NULL)
            """),
            {"device_id": device_id, "user_id": user_id, "attested_at": now},
        )

    return ticket_id


async def test_issue_qr_success(client, test_session_factory, make_auth_headers):
    user_id = uuid.uuid4()
    device_id = uuid.uuid4()
    ticket_id = await _seed_qr_data(
        test_session_factory, user_id=user_id, device_id=device_id, ticket_state="issued"
    )
    headers = make_auth_headers(user_id, device_id)

    response = await client.get(
        f"/v1/tickets/{ticket_id}/qr",
        params={"latitude": 0.0, "longitude": 0.0},
        headers=headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert "jwt" in body
    assert "jti" in body
    assert body["ticket_id"] == str(ticket_id)


async def test_issue_qr_no_auth(client):
    response = await client.get(
        f"/v1/tickets/{uuid.uuid4()}/qr",
        params={"latitude": 0.0, "longitude": 0.0},
    )

    assert response.status_code == 401


async def test_issue_qr_ticket_not_found(client, make_auth_headers):
    user_id = uuid.uuid4()
    device_id = uuid.uuid4()
    headers = make_auth_headers(user_id, device_id)

    response = await client.get(
        f"/v1/tickets/{uuid.uuid4()}/qr",
        params={"latitude": 0.0, "longitude": 0.0},
        headers=headers,
    )

    assert response.status_code == 404


async def test_issue_qr_wrong_state(client, test_session_factory, make_auth_headers):
    user_id = uuid.uuid4()
    device_id = uuid.uuid4()
    ticket_id = await _seed_qr_data(
        test_session_factory, user_id=user_id, device_id=device_id, ticket_state="cancelled"
    )
    headers = make_auth_headers(user_id, device_id)

    response = await client.get(
        f"/v1/tickets/{ticket_id}/qr",
        params={"latitude": 0.0, "longitude": 0.0},
        headers=headers,
    )

    assert response.status_code == 409
