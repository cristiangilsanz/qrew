import uuid

import httpx
import pytest

pytestmark = pytest.mark.asyncio(loop_scope="session")

_INTERNAL_HEADERS = {"X-Internal-Key": "test-internal-key"}


@pytest.mark.integration
async def test_create_charge_success(
    client: httpx.AsyncClient,
    auth_headers: tuple[uuid.UUID, dict[str, str]],
    seed_event: tuple[uuid.UUID, uuid.UUID],
) -> None:
    event_id, ticket_type_id = seed_event
    user_id, headers = auth_headers
    create_resp = await client.post(
        f"/v1/events/{event_id}/reserve",
        json={"ticket_type_id": str(ticket_type_id), "quantity": 2},
        headers=headers,
    )
    assert create_resp.status_code == 201
    reservation_id = create_resp.json()["id"]

    charge_resp = await client.post(
        f"/v1/billing/reservations/{reservation_id}/charge",
        json={"user_id": str(user_id)},
        headers=_INTERNAL_HEADERS,
    )
    assert charge_resp.status_code == 200
    data = charge_resp.json()
    assert data["amount_cents"] == 3000  # 1500 * 2
    assert data["currency"] == "EUR"


@pytest.mark.integration
async def test_create_charge_no_internal_key(
    client: httpx.AsyncClient,
    auth_headers: tuple[uuid.UUID, dict[str, str]],
    seed_event: tuple[uuid.UUID, uuid.UUID],
) -> None:
    event_id, ticket_type_id = seed_event
    user_id, headers = auth_headers
    create_resp = await client.post(
        f"/v1/events/{event_id}/reserve",
        json={"ticket_type_id": str(ticket_type_id), "quantity": 1},
        headers=headers,
    )
    assert create_resp.status_code == 201
    reservation_id = create_resp.json()["id"]

    charge_resp = await client.post(
        f"/v1/billing/reservations/{reservation_id}/charge",
        json={"user_id": str(user_id)},
    )
    assert charge_resp.status_code == 401


@pytest.mark.integration
async def test_create_charge_not_found(
    client: httpx.AsyncClient,
) -> None:
    resp = await client.post(
        f"/v1/billing/reservations/{uuid.uuid4()}/charge",
        json={"user_id": str(uuid.uuid4())},
        headers=_INTERNAL_HEADERS,
    )
    assert resp.status_code == 404
