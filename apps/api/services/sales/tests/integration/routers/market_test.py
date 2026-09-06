# tests the market endpoints that expose the resale waitlist and its offers
import uuid as _uuid

import httpx
import pytest

pytestmark = pytest.mark.asyncio(loop_scope="session")


# verifies that the waitlist stays closed while the sale is still running
@pytest.mark.integration
async def test_join_waitlist_rejected_while_the_sale_is_open(
    client: httpx.AsyncClient,
    auth_headers: tuple[_uuid.UUID, dict[str, str]],
    seed_event: tuple[_uuid.UUID, _uuid.UUID],
) -> None:
    event_id, _ = seed_event
    _, headers = auth_headers
    response = await client.post(f"/v1/events/{event_id}/market/queue/join", headers=headers)
    assert response.status_code == 404


# verifies that an unknown event cannot be joined
@pytest.mark.integration
async def test_join_waitlist_rejects_an_unknown_event(
    client: httpx.AsyncClient,
    auth_headers: tuple[_uuid.UUID, dict[str, str]],
) -> None:
    _, headers = auth_headers
    response = await client.post(f"/v1/events/{_uuid.uuid4()}/market/queue/join", headers=headers)
    assert response.status_code == 404


# verifies that joining a closed sale reports the place and shows up in the status
@pytest.mark.integration
async def test_join_and_read_the_waitlist(
    client: httpx.AsyncClient,
    auth_headers: tuple[_uuid.UUID, dict[str, str]],
    closed_event: _uuid.UUID,
) -> None:
    _, headers = auth_headers
    joined = await client.post(f"/v1/events/{closed_event}/market/queue/join", headers=headers)
    assert joined.status_code == 200

    status = await client.get(f"/v1/events/{closed_event}/market/queue/status", headers=headers)
    assert status.status_code == 200
    body = status.json()
    assert body["in_queue"] is True
    assert body["queue_count"] >= 1

    mine = await client.get("/v1/market/queues", headers=headers)
    assert mine.status_code == 200
    assert any(entry["event_id"] == str(closed_event) for entry in mine.json())


# verifies that joining twice keeps the single place already held
@pytest.mark.integration
async def test_joining_twice_keeps_one_place(
    client: httpx.AsyncClient,
    auth_headers: tuple[_uuid.UUID, dict[str, str]],
    closed_event: _uuid.UUID,
) -> None:
    _, headers = auth_headers
    await client.post(f"/v1/events/{closed_event}/market/queue/join", headers=headers)
    await client.post(f"/v1/events/{closed_event}/market/queue/join", headers=headers)
    status = await client.get(f"/v1/events/{closed_event}/market/queue/status", headers=headers)
    assert status.json()["queue_count"] == 1


# verifies that leaving the waitlist clears the standing
@pytest.mark.integration
async def test_leave_the_waitlist(
    client: httpx.AsyncClient,
    auth_headers: tuple[_uuid.UUID, dict[str, str]],
    closed_event: _uuid.UUID,
) -> None:
    _, headers = auth_headers
    await client.post(f"/v1/events/{closed_event}/market/queue/join", headers=headers)
    left = await client.delete(f"/v1/events/{closed_event}/market/queue/leave", headers=headers)
    assert left.status_code in (200, 204)

    status = await client.get(f"/v1/events/{closed_event}/market/queue/status", headers=headers)
    assert status.json()["in_queue"] is False


# verifies that a caller with no offers gets an empty list rather than an error
@pytest.mark.integration
async def test_offers_start_empty(
    client: httpx.AsyncClient,
    auth_headers: tuple[_uuid.UUID, dict[str, str]],
) -> None:
    _, headers = auth_headers
    listed = await client.get("/v1/market/assignments", headers=headers)
    assert listed.status_code == 200
    assert listed.json() == []

    pending = await client.get("/v1/market/assignments/pending", headers=headers)
    assert pending.status_code == 200
    assert pending.json() is None


# verifies that another caller's offer is never readable
@pytest.mark.integration
async def test_reading_an_unknown_offer_is_refused(
    client: httpx.AsyncClient,
    auth_headers: tuple[_uuid.UUID, dict[str, str]],
) -> None:
    _, headers = auth_headers
    response = await client.get(f"/v1/market/assignments/{_uuid.uuid4()}", headers=headers)
    assert response.status_code == 404
