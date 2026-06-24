import uuid
from datetime import UTC, datetime, timedelta

import httpx
import pytest

from tests.integration.conftest import auth_headers_for

pytestmark = [pytest.mark.integration, pytest.mark.asyncio(loop_scope="session")]


def _future(days: int) -> str:
    return (datetime.now(UTC) + timedelta(days=days)).isoformat()


async def _setup_org_venue_event(
    client: httpx.AsyncClient, user_id: uuid.UUID
) -> tuple[str, str, str, dict]:
    """Create an org, a venue, and a draft event. Returns (org_id, venue_id, event_id, headers)."""
    headers = auth_headers_for(user_id)

    org_resp = await client.post(
        "/v1/organisations",
        json={
            "slug": f"ev-org-{uuid.uuid4().hex[:8]}",
            "name": "Event Test Org",
        },
        headers=headers,
    )
    assert org_resp.status_code == 201
    org_id = org_resp.json()["id"]

    venue_resp = await client.post(
        "/v1/venues",
        json={
            "name": "Event Test Venue",
            "address_line": "1 Test Ave",
            "city": "Berlin",
            "country": "DE",
            "latitude": "52.5200",
            "longitude": "13.4050",
            "geofence_radius_m": 300,
            "timezone": "Europe/Berlin",
        },
        headers=headers,
    )
    assert venue_resp.status_code == 201
    venue_id = venue_resp.json()["id"]

    event_resp = await client.post(
        f"/v1/organisations/{org_id}/events",
        json={
            "venue_id": venue_id,
            "name": "Integration Test Event",
            "starts_at": _future(30),
            "ends_at": _future(31),
            "sale_starts_at": _future(1),
            "sale_ends_at": _future(29),
        },
        headers=headers,
    )
    assert event_resp.status_code == 201
    event_id = event_resp.json()["id"]

    return org_id, venue_id, event_id, headers


# ---------------------------------------------------------------------------
# Event management
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_event(client: httpx.AsyncClient, user_id: uuid.UUID) -> None:
    _, _, event_id, headers = await _setup_org_venue_event(client, user_id)
    resp = await client.patch(
        f"/v1/events/{event_id}",
        json={"name": "Updated Event Name"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "Updated Event Name"


@pytest.mark.asyncio
async def test_update_event_unauthenticated(client: httpx.AsyncClient, user_id: uuid.UUID) -> None:
    _, _, event_id, _ = await _setup_org_venue_event(client, user_id)
    resp = await client.patch(f"/v1/events/{event_id}", json={"name": "Should Fail"})
    assert resp.status_code in {401, 403}


@pytest.mark.asyncio
async def test_update_event_forbidden_non_member(
    client: httpx.AsyncClient, user_id: uuid.UUID
) -> None:
    _, _, event_id, _ = await _setup_org_venue_event(client, user_id)
    other_headers = auth_headers_for(uuid.uuid4())
    resp = await client.patch(
        f"/v1/events/{event_id}", json={"name": "Should Fail"}, headers=other_headers
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_publish_event(client: httpx.AsyncClient, user_id: uuid.UUID) -> None:
    _, _, event_id, headers = await _setup_org_venue_event(client, user_id)
    resp = await client.post(f"/v1/events/{event_id}/publish", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "published"


@pytest.mark.asyncio
async def test_cancel_event(client: httpx.AsyncClient, user_id: uuid.UUID) -> None:
    _, _, event_id, headers = await _setup_org_venue_event(client, user_id)
    await client.post(f"/v1/events/{event_id}/publish", headers=headers)
    resp = await client.post(f"/v1/events/{event_id}/cancel", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "cancelled"


# ---------------------------------------------------------------------------
# Public catalog
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_search_events_returns_published(
    client: httpx.AsyncClient, user_id: uuid.UUID
) -> None:
    _, _, event_id, headers = await _setup_org_venue_event(client, user_id)
    await client.post(f"/v1/events/{event_id}/publish", headers=headers)

    resp = await client.get("/v1/events")
    assert resp.status_code == 200
    ids = [item["id"] for item in resp.json()["items"]]
    assert event_id in ids


@pytest.mark.asyncio
async def test_get_public_event(client: httpx.AsyncClient, user_id: uuid.UUID) -> None:
    _, _, event_id, headers = await _setup_org_venue_event(client, user_id)
    await client.post(f"/v1/events/{event_id}/publish", headers=headers)

    resp = await client.get(f"/v1/events/{event_id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == event_id
    assert "organisation" in body
    assert "venue" in body
    assert "ticket_types" in body


@pytest.mark.asyncio
async def test_get_public_event_not_found(client: httpx.AsyncClient) -> None:
    resp = await client.get(f"/v1/events/{uuid.uuid4()}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_public_event_draft_not_visible(
    client: httpx.AsyncClient, user_id: uuid.UUID
) -> None:
    _, _, event_id, _ = await _setup_org_venue_event(client, user_id)
    resp = await client.get(f"/v1/events/{event_id}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_event_availability(client: httpx.AsyncClient, user_id: uuid.UUID) -> None:
    _, _, event_id, headers = await _setup_org_venue_event(client, user_id)
    await client.post(f"/v1/events/{event_id}/publish", headers=headers)

    resp = await client.get(f"/v1/events/{event_id}/availability")
    assert resp.status_code == 200
    assert "ticket_types" in resp.json()


@pytest.mark.asyncio
async def test_get_event_availability_not_found(client: httpx.AsyncClient) -> None:
    resp = await client.get(f"/v1/events/{uuid.uuid4()}/availability")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Ticket types
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_ticket_type(client: httpx.AsyncClient, user_id: uuid.UUID) -> None:
    _, _, event_id, headers = await _setup_org_venue_event(client, user_id)
    resp = await client.post(
        f"/v1/events/{event_id}/ticket-types",
        json={
            "name": "General Admission",
            "capacity": 100,
            "price_cents": 2500,
            "currency": "EUR",
            "position": 0,
        },
        headers=headers,
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["event_id"] == event_id
    assert body["name"] == "General Admission"
    assert body["available"] == 100


@pytest.mark.asyncio
async def test_list_ticket_types(client: httpx.AsyncClient, user_id: uuid.UUID) -> None:
    _, _, event_id, headers = await _setup_org_venue_event(client, user_id)
    await client.post(
        f"/v1/events/{event_id}/ticket-types",
        json={"name": "VIP", "capacity": 50, "price_cents": 5000, "currency": "EUR"},
        headers=headers,
    )

    resp = await client.get(f"/v1/events/{event_id}/ticket-types")
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) >= 1
    assert any(item["name"] == "VIP" for item in items)


@pytest.mark.asyncio
async def test_update_ticket_type(client: httpx.AsyncClient, user_id: uuid.UUID) -> None:
    _, _, event_id, headers = await _setup_org_venue_event(client, user_id)
    create_resp = await client.post(
        f"/v1/events/{event_id}/ticket-types",
        json={"name": "Early Bird", "capacity": 30, "price_cents": 1000, "currency": "EUR"},
        headers=headers,
    )
    assert create_resp.status_code == 201
    ticket_type_id = create_resp.json()["id"]

    resp = await client.patch(
        f"/v1/events/{event_id}/ticket-types/{ticket_type_id}",
        json={"price_cents": 1500},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["price_cents"] == 1500


@pytest.mark.asyncio
async def test_delete_ticket_type(client: httpx.AsyncClient, user_id: uuid.UUID) -> None:
    _, _, event_id, headers = await _setup_org_venue_event(client, user_id)
    create_resp = await client.post(
        f"/v1/events/{event_id}/ticket-types",
        json={"name": "To Delete", "capacity": 10, "price_cents": 500, "currency": "EUR"},
        headers=headers,
    )
    assert create_resp.status_code == 201
    ticket_type_id = create_resp.json()["id"]

    resp = await client.delete(
        f"/v1/events/{event_id}/ticket-types/{ticket_type_id}", headers=headers
    )
    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_create_ticket_type_unauthenticated(
    client: httpx.AsyncClient, user_id: uuid.UUID
) -> None:
    _, _, event_id, _ = await _setup_org_venue_event(client, user_id)
    resp = await client.post(
        f"/v1/events/{event_id}/ticket-types",
        json={"name": "No Auth", "capacity": 10, "price_cents": 0, "currency": "EUR"},
    )
    assert resp.status_code in {401, 403}
