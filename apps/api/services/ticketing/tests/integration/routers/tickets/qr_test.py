# tests qr
import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import text

pytestmark = [pytest.mark.integration, pytest.mark.asyncio(loop_scope="session")]


# seed a ticket + event_venue_context + device_context for gate evaluation
async def _seed_qr_data(
    session_factory,
    *,
    user_id: uuid.UUID,
    device_id: uuid.UUID,
    ticket_state: str = "issued",
) -> uuid.UUID:
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


# verifies that issue qr success
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


# verifies that issue qr no auth
async def test_issue_qr_no_auth(client):
    response = await client.get(
        f"/v1/tickets/{uuid.uuid4()}/qr",
        params={"latitude": 0.0, "longitude": 0.0},
    )

    assert response.status_code == 401


# verifies that issue qr ticket not found
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


# verifies that issue qr wrong state
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


# verifies that a fix the handset calls simulated is refused at the gate
async def test_issue_qr_denies_a_simulated_location(
    client, test_session_factory, make_auth_headers, monkeypatch
):
    from com.qode.qrew.v1.ticketing.core.config import settings

    monkeypatch.setattr(settings, "ticket_qr_require_location_integrity", True)
    user_id = uuid.uuid4()
    device_id = uuid.uuid4()
    ticket_id = await _seed_qr_data(
        test_session_factory, user_id=user_id, device_id=device_id, ticket_state="issued"
    )
    headers = make_auth_headers(user_id, device_id)

    response = await client.get(
        f"/v1/tickets/{ticket_id}/qr",
        params={"latitude": 0.0, "longitude": 0.0, "location_is_mock": True},
        headers=headers,
    )

    assert response.status_code == 403
    assert response.json()["detail"]["field"] == "location_mock"


# verifies that a caller with no such signal still gets its code
async def test_issue_qr_allows_a_caller_without_the_signal(
    client, test_session_factory, make_auth_headers, monkeypatch
):
    from com.qode.qrew.v1.ticketing.core.config import settings

    monkeypatch.setattr(settings, "ticket_qr_require_location_integrity", True)
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
    assert "jwt" in response.json()


# verifies that a handset vouching for its fix is let through
async def test_issue_qr_allows_a_genuine_location(
    client, test_session_factory, make_auth_headers, monkeypatch
):
    from com.qode.qrew.v1.ticketing.core.config import settings

    monkeypatch.setattr(settings, "ticket_qr_require_location_integrity", True)
    user_id = uuid.uuid4()
    device_id = uuid.uuid4()
    ticket_id = await _seed_qr_data(
        test_session_factory, user_id=user_id, device_id=device_id, ticket_state="issued"
    )
    headers = make_auth_headers(user_id, device_id)

    response = await client.get(
        f"/v1/tickets/{ticket_id}/qr",
        params={"latitude": 0.0, "longitude": 0.0, "location_is_mock": False},
        headers=headers,
    )

    assert response.status_code == 200
    assert "jwt" in response.json()


# verifies that the gate reports the checks it will actually evaluate
async def test_gate_requirements_reports_the_switches(client, make_auth_headers, monkeypatch):
    from com.qode.qrew.v1.ticketing.core.config import settings

    monkeypatch.setattr(settings, "ticket_qr_require_reassertion", False)
    monkeypatch.setattr(settings, "ticket_qr_require_geofence", True)
    monkeypatch.setattr(settings, "ticket_qr_require_device_binding", False)
    monkeypatch.setattr(settings, "ticket_qr_require_attestation", False)
    monkeypatch.setattr(settings, "ticket_qr_require_location_integrity", True)
    headers = make_auth_headers(uuid.uuid4(), uuid.uuid4())

    response = await client.get("/v1/tickets/qr/requirements", headers=headers)

    assert response.status_code == 200
    assert response.json() == {
        "reassertion": False,
        "geofence": True,
        "device_binding": False,
        "attestation": False,
        "location_integrity": True,
    }


# verifies that the requirements are not readable without a token
async def test_gate_requirements_needs_a_token(client):
    response = await client.get("/v1/tickets/qr/requirements")

    assert response.status_code == 401
