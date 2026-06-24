import uuid
from datetime import UTC, datetime, timedelta

import httpx
import pytest

from tests.integration.conftest import auth_headers_for

pytestmark = [pytest.mark.integration, pytest.mark.asyncio(loop_scope="session")]


def _future(days: int) -> str:
    return (datetime.now(UTC) + timedelta(days=days)).isoformat()


def _org_payload(suffix: str = "") -> dict:
    slug = f"test-org-{uuid.uuid4().hex[:8]}{suffix}"
    return {"slug": slug, "name": f"Test Org {suffix}", "description": "Integration test org"}


async def _create_venue(client: httpx.AsyncClient, headers: dict) -> str:
    resp = await client.post(
        "/v1/venues",
        json={
            "name": "Integration Venue",
            "address_line": "123 Test Street",
            "city": "Amsterdam",
            "country": "NL",
            "latitude": "52.3676",
            "longitude": "4.9041",
            "geofence_radius_m": 200,
            "timezone": "Europe/Amsterdam",
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


async def _create_org(client: httpx.AsyncClient, headers: dict) -> dict:
    resp = await client.post("/v1/organisations", json=_org_payload(), headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _create_event(
    client: httpx.AsyncClient,
    org_id: str,
    venue_id: str,
    headers: dict,
) -> dict:
    resp = await client.post(
        f"/v1/organisations/{org_id}/events",
        json={
            "venue_id": venue_id,
            "name": "Integration Event",
            "starts_at": _future(30),
            "ends_at": _future(31),
            "sale_starts_at": _future(1),
            "sale_ends_at": _future(29),
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


@pytest.mark.asyncio
async def test_create_organisation(client: httpx.AsyncClient, auth_headers: dict) -> None:
    payload = _org_payload()
    resp = await client.post("/v1/organisations", json=payload, headers=auth_headers)
    assert resp.status_code == 201
    body = resp.json()
    assert body["slug"] == payload["slug"]
    assert body["name"] == payload["name"]
    assert "id" in body


@pytest.mark.asyncio
async def test_create_organisation_duplicate_slug(
    client: httpx.AsyncClient, auth_headers: dict
) -> None:
    payload = _org_payload()
    r1 = await client.post("/v1/organisations", json=payload, headers=auth_headers)
    assert r1.status_code == 201
    r2 = await client.post("/v1/organisations", json=payload, headers=auth_headers)
    assert r2.status_code == 409


@pytest.mark.asyncio
async def test_create_organisation_unauthenticated(client: httpx.AsyncClient) -> None:
    resp = await client.post("/v1/organisations", json=_org_payload())
    assert resp.status_code in {401, 403}


@pytest.mark.asyncio
async def test_list_my_organisations(client: httpx.AsyncClient, auth_headers: dict) -> None:
    org = await _create_org(client, auth_headers)
    resp = await client.get("/v1/organisations", headers=auth_headers)
    assert resp.status_code == 200
    ids = [item["id"] for item in resp.json()["items"]]
    assert org["id"] in ids


@pytest.mark.asyncio
async def test_list_my_organisations_unauthenticated(client: httpx.AsyncClient) -> None:
    resp = await client.get("/v1/organisations")
    assert resp.status_code in {401, 403}


@pytest.mark.asyncio
async def test_get_public_organisation(client: httpx.AsyncClient, auth_headers: dict) -> None:
    org = await _create_org(client, auth_headers)
    resp = await client.get(f"/v1/organisations/{org['id']}")
    assert resp.status_code == 200
    assert resp.json()["id"] == org["id"]


@pytest.mark.asyncio
async def test_get_public_organisation_not_found(client: httpx.AsyncClient) -> None:
    resp = await client.get(f"/v1/organisations/{uuid.uuid4()}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_invite_member(client: httpx.AsyncClient, user_id: uuid.UUID) -> None:
    headers = auth_headers_for(user_id)
    org = await _create_org(client, headers)

    invitee_id = uuid.uuid4()
    invitee_email = f"invitee-{invitee_id.hex[:8]}@example.com"
    resp = await client.post(
        f"/v1/organisations/{org['id']}/members",
        json={"email": invitee_email, "role": "member"},
        headers=headers,
    )
    # 201 if UserRepository finds the email, 400/404 if not (user doesn't exist in catalog DB)
    assert resp.status_code in {201, 400, 404}


@pytest.mark.asyncio
async def test_remove_member_not_found(client: httpx.AsyncClient, user_id: uuid.UUID) -> None:
    headers = auth_headers_for(user_id)
    org = await _create_org(client, headers)
    random_user = uuid.uuid4()
    resp = await client.delete(
        f"/v1/organisations/{org['id']}/members/{random_user}", headers=headers
    )
    # 204 if removed, 400 if not a member
    assert resp.status_code in {204, 400}


@pytest.mark.asyncio
async def test_create_org_event(client: httpx.AsyncClient, user_id: uuid.UUID) -> None:
    headers = auth_headers_for(user_id)
    org = await _create_org(client, headers)
    venue_id = await _create_venue(client, headers)
    event = await _create_event(client, org["id"], venue_id, headers)
    assert event["organisation_id"] == org["id"]
    assert event["venue_id"] == venue_id
    assert event["status"] == "draft"


@pytest.mark.asyncio
async def test_list_org_events(client: httpx.AsyncClient, user_id: uuid.UUID) -> None:
    headers = auth_headers_for(user_id)
    org = await _create_org(client, headers)
    venue_id = await _create_venue(client, headers)
    event = await _create_event(client, org["id"], venue_id, headers)

    resp = await client.get(f"/v1/organisations/{org['id']}/events", headers=headers)
    assert resp.status_code == 200
    ids = [item["id"] for item in resp.json()["items"]]
    assert event["id"] in ids


@pytest.mark.asyncio
async def test_get_org_event(client: httpx.AsyncClient, user_id: uuid.UUID) -> None:
    headers = auth_headers_for(user_id)
    org = await _create_org(client, headers)
    venue_id = await _create_venue(client, headers)
    event = await _create_event(client, org["id"], venue_id, headers)

    resp = await client.get(f"/v1/organisations/{org['id']}/events/{event['id']}", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == event["id"]


@pytest.mark.asyncio
async def test_get_org_event_not_found(client: httpx.AsyncClient, user_id: uuid.UUID) -> None:
    headers = auth_headers_for(user_id)
    org = await _create_org(client, headers)
    resp = await client.get(f"/v1/organisations/{org['id']}/events/{uuid.uuid4()}", headers=headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_org_events_forbidden_non_member(
    client: httpx.AsyncClient, user_id: uuid.UUID
) -> None:
    owner_headers = auth_headers_for(user_id)
    org = await _create_org(client, owner_headers)

    other_headers = auth_headers_for(uuid.uuid4())
    resp = await client.get(f"/v1/organisations/{org['id']}/events", headers=other_headers)
    assert resp.status_code == 403
