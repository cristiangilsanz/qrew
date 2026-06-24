import uuid

import httpx
import pytest

pytestmark = pytest.mark.asyncio(loop_scope="session")


@pytest.mark.integration
async def test_create_reservation_success(
    client: httpx.AsyncClient,
    auth_headers: tuple[uuid.UUID, dict[str, str]],
    seed_event: tuple[uuid.UUID, uuid.UUID],
) -> None:
    event_id, ticket_type_id = seed_event
    _, headers = auth_headers
    resp = await client.post(
        f"/v1/events/{event_id}/reserve",
        json={"ticket_type_id": str(ticket_type_id), "quantity": 2},
        headers=headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["event_id"] == str(event_id)
    assert data["ticket_type_id"] == str(ticket_type_id)
    assert data["quantity"] == 2
    assert data["status"] == "reserved"


@pytest.mark.integration
async def test_create_reservation_event_not_found(
    client: httpx.AsyncClient,
    auth_headers: tuple[uuid.UUID, dict[str, str]],
) -> None:
    _, headers = auth_headers
    resp = await client.post(
        f"/v1/events/{uuid.uuid4()}/reserve",
        json={"ticket_type_id": str(uuid.uuid4()), "quantity": 1},
        headers=headers,
    )
    assert resp.status_code == 404


@pytest.mark.integration
async def test_create_reservation_sold_out(
    client: httpx.AsyncClient,
    auth_headers: tuple[uuid.UUID, dict[str, str]],
    test_session_factory: object,
) -> None:
    from sqlalchemy import text
    from datetime import UTC, datetime, timedelta

    factory = test_session_factory  # type: ignore[assignment]
    event_id = uuid.uuid4()
    ticket_type_id = uuid.uuid4()
    now = datetime.now(UTC)
    async with factory() as session, session.begin():  # type: ignore[union-attr]
        await session.execute(
            text("""
                INSERT INTO sales.event_context
                (event_id, status, sale_starts_at, sale_ends_at, max_tickets_per_user,
                 queue_required, queue_admit_rate_per_minute)
                VALUES (:event_id, 'published', :sale_starts, :sale_ends, 10, false, 50)
            """),
            {
                "event_id": event_id,
                "sale_starts": now - timedelta(hours=1),
                "sale_ends": now + timedelta(hours=1),
            },
        )
        await session.execute(
            text("""
                INSERT INTO sales.ticket_type_inventory
                (ticket_type_id, event_id, capacity, reserved_count, price_cents, currency)
                VALUES (:ticket_type_id, :event_id, 0, 0, 1000, 'EUR')
            """),
            {"ticket_type_id": ticket_type_id, "event_id": event_id},
        )

    _, headers = auth_headers
    resp = await client.post(
        f"/v1/events/{event_id}/reserve",
        json={"ticket_type_id": str(ticket_type_id), "quantity": 1},
        headers=headers,
    )
    assert resp.status_code == 409


@pytest.mark.integration
async def test_get_reservation_success(
    client: httpx.AsyncClient,
    auth_headers: tuple[uuid.UUID, dict[str, str]],
    seed_event: tuple[uuid.UUID, uuid.UUID],
) -> None:
    event_id, ticket_type_id = seed_event
    _, headers = auth_headers
    create_resp = await client.post(
        f"/v1/events/{event_id}/reserve",
        json={"ticket_type_id": str(ticket_type_id), "quantity": 1},
        headers=headers,
    )
    assert create_resp.status_code == 201
    reservation_id = create_resp.json()["id"]

    get_resp = await client.get(f"/v1/reservations/{reservation_id}", headers=headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == reservation_id


@pytest.mark.integration
async def test_get_reservation_not_owned(
    client: httpx.AsyncClient,
    auth_headers: tuple[uuid.UUID, dict[str, str]],
    seed_event: tuple[uuid.UUID, uuid.UUID],
) -> None:
    import time

    from com.qode.qrew.v1.sales.core.principals import ACCESS, sign

    event_id, ticket_type_id = seed_event
    user_id, headers = auth_headers
    create_resp = await client.post(
        f"/v1/events/{event_id}/reserve",
        json={"ticket_type_id": str(ticket_type_id), "quantity": 1},
        headers=headers,
    )
    assert create_resp.status_code == 201
    reservation_id = create_resp.json()["id"]

    other_id = uuid.uuid4()
    now = int(time.time())
    other_token = sign(
        ACCESS, {"sub": str(other_id), "type": "access", "iat": now, "exp": now + 3600}
    )
    other_headers = {"Authorization": f"Bearer {other_token}"}
    get_resp = await client.get(f"/v1/reservations/{reservation_id}", headers=other_headers)
    assert get_resp.status_code == 404


@pytest.mark.integration
async def test_cancel_reservation_success(
    client: httpx.AsyncClient,
    auth_headers: tuple[uuid.UUID, dict[str, str]],
    seed_event: tuple[uuid.UUID, uuid.UUID],
) -> None:
    event_id, ticket_type_id = seed_event
    _, headers = auth_headers
    create_resp = await client.post(
        f"/v1/events/{event_id}/reserve",
        json={"ticket_type_id": str(ticket_type_id), "quantity": 1},
        headers=headers,
    )
    assert create_resp.status_code == 201
    reservation_id = create_resp.json()["id"]

    cancel_resp = await client.post(f"/v1/reservations/{reservation_id}/cancel", headers=headers)
    assert cancel_resp.status_code == 200
    assert cancel_resp.json()["status"] == "cancelled"
