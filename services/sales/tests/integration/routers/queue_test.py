import uuid

import httpx
import pytest

pytestmark = pytest.mark.asyncio(loop_scope="session")


@pytest.mark.integration
async def test_join_queue_success(
    client: httpx.AsyncClient,
    auth_headers: tuple[uuid.UUID, dict[str, str]],
    seed_queue_event: tuple[uuid.UUID, uuid.UUID],
) -> None:
    event_id, _ = seed_queue_event
    _, headers = auth_headers
    resp = await client.post(f"/v1/events/{event_id}/queue/join", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["position"] >= 1


@pytest.mark.integration
async def test_join_queue_no_queue_on_non_queue_event(
    client: httpx.AsyncClient,
    auth_headers: tuple[uuid.UUID, dict[str, str]],
    seed_event: tuple[uuid.UUID, uuid.UUID],
) -> None:
    event_id, _ = seed_event
    _, headers = auth_headers
    resp = await client.post(f"/v1/events/{event_id}/queue/join", headers=headers)
    assert resp.status_code == 409


@pytest.mark.integration
async def test_join_queue_event_not_found(
    client: httpx.AsyncClient,
    auth_headers: tuple[uuid.UUID, dict[str, str]],
) -> None:
    _, headers = auth_headers
    resp = await client.post(f"/v1/events/{uuid.uuid4()}/queue/join", headers=headers)
    assert resp.status_code == 404


@pytest.mark.integration
async def test_queue_position_not_in_queue(
    client: httpx.AsyncClient,
    auth_headers: tuple[uuid.UUID, dict[str, str]],
    seed_queue_event: tuple[uuid.UUID, uuid.UUID],
) -> None:
    event_id, _ = seed_queue_event
    _, headers = auth_headers
    resp = await client.get(f"/v1/events/{event_id}/queue/position", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["position"] is None


@pytest.mark.integration
async def test_queue_position_after_join(
    client: httpx.AsyncClient,
    auth_headers: tuple[uuid.UUID, dict[str, str]],
    seed_queue_event: tuple[uuid.UUID, uuid.UUID],
) -> None:
    event_id, _ = seed_queue_event
    _, headers = auth_headers
    join_resp = await client.post(f"/v1/events/{event_id}/queue/join", headers=headers)
    assert join_resp.status_code == 200

    pos_resp = await client.get(f"/v1/events/{event_id}/queue/position", headers=headers)
    assert pos_resp.status_code == 200
    assert pos_resp.json()["position"] >= 1
