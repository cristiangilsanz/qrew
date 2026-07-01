import uuid

import httpx
import pytest

pytestmark = [pytest.mark.integration, pytest.mark.asyncio(loop_scope="session")]

_VENUE_PAYLOAD = {
    "name": "Test Venue",
    "address_line": "1 Main Street",
    "city": "Amsterdam",
    "country": "NL",
    "latitude": "52.3676",
    "longitude": "4.9041",
    "geofence_radius_m": 200,
    "timezone": "Europe/Amsterdam",
    "description": "Integration test venue",
}


def _venue_payload(city: str = "Amsterdam", country: str = "NL") -> dict:
    return {**_VENUE_PAYLOAD, "city": city, "country": country}


@pytest.mark.asyncio
async def test_create_venue(client: httpx.AsyncClient, auth_headers: dict) -> None:
    resp = await client.post("/v1/venues", json=_VENUE_PAYLOAD, headers=auth_headers)
    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == _VENUE_PAYLOAD["name"]
    assert body["city"] == _VENUE_PAYLOAD["city"]
    assert "id" in body


@pytest.mark.asyncio
async def test_create_venue_unauthenticated(client: httpx.AsyncClient) -> None:
    resp = await client.post("/v1/venues", json=_VENUE_PAYLOAD)
    assert resp.status_code in {401, 403}


@pytest.mark.asyncio
async def test_list_venues(client: httpx.AsyncClient, auth_headers: dict) -> None:
    resp1 = await client.post("/v1/venues", json=_venue_payload(), headers=auth_headers)
    assert resp1.status_code == 201
    venue_id = resp1.json()["id"]

    resp = await client.get("/v1/venues")
    assert resp.status_code == 200
    ids = [item["id"] for item in resp.json()["items"]]
    assert venue_id in ids


@pytest.mark.asyncio
async def test_list_venues_filter_by_city(client: httpx.AsyncClient, auth_headers: dict) -> None:
    city = f"TestCity{uuid.uuid4().hex[:6]}"
    r = await client.post("/v1/venues", json=_venue_payload(city=city), headers=auth_headers)
    assert r.status_code == 201
    venue_id = r.json()["id"]

    resp = await client.get(f"/v1/venues?city={city}")
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert any(item["id"] == venue_id for item in items)
    assert all(item["city"] == city for item in items)


@pytest.mark.asyncio
async def test_list_venues_filter_by_country(client: httpx.AsyncClient, auth_headers: dict) -> None:
    r = await client.post("/v1/venues", json=_venue_payload(country="DE"), headers=auth_headers)
    assert r.status_code == 201
    venue_id = r.json()["id"]

    resp = await client.get("/v1/venues?country=DE")
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert any(item["id"] == venue_id for item in items)


@pytest.mark.asyncio
async def test_get_venue(client: httpx.AsyncClient, auth_headers: dict) -> None:
    r = await client.post("/v1/venues", json=_VENUE_PAYLOAD, headers=auth_headers)
    assert r.status_code == 201
    venue_id = r.json()["id"]

    resp = await client.get(f"/v1/venues/{venue_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == venue_id


@pytest.mark.asyncio
async def test_get_venue_not_found(client: httpx.AsyncClient) -> None:
    resp = await client.get(f"/v1/venues/{uuid.uuid4()}")
    assert resp.status_code == 404
