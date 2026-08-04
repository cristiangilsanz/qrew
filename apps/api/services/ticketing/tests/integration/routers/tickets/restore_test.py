import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import text

pytestmark = [pytest.mark.integration, pytest.mark.asyncio(loop_scope="session")]


async def _seed_on_sale_ticket(
    session_factory,
    *,
    user_id: uuid.UUID,
    bound_device_id: uuid.UUID | None = None,
) -> uuid.UUID:
    ticket_id = uuid.uuid4()
    async with session_factory() as session, session.begin():
        await session.execute(
            text("""
                INSERT INTO ticketing.tickets
                    (id, reservation_id, event_id, ticket_type_id, owner_user_id, bound_device_id, state)
                VALUES (:id, :res_id, :ev_id, :tt_id, :owner_id, :bound_device, 'on_sale')
            """),
            {
                "id": ticket_id,
                "res_id": uuid.uuid4(),
                "ev_id": uuid.uuid4(),
                "tt_id": uuid.uuid4(),
                "owner_id": user_id,
                "bound_device": bound_device_id,
            },
        )
    return ticket_id


async def _seed_device(session_factory, *, device_id: uuid.UUID, user_id: uuid.UUID) -> None:
    now = datetime.now(UTC)
    async with session_factory() as session, session.begin():
        await session.execute(
            text("""
                INSERT INTO ticketing.device_context
                    (device_id, user_id, attested_at, revoked_at)
                VALUES (:device_id, :user_id, :attested_at, NULL)
            """),
            {"device_id": device_id, "user_id": user_id, "attested_at": now},
        )


async def test_restore_frozen_ticket_success(client, test_session_factory, make_auth_headers):
    user_id = uuid.uuid4()
    old_device_id = uuid.uuid4()
    new_device_id = uuid.uuid4()

    ticket_id = await _seed_on_sale_ticket(
        test_session_factory, user_id=user_id, bound_device_id=old_device_id
    )
    await _seed_device(test_session_factory, device_id=new_device_id, user_id=user_id)

    headers = make_auth_headers(user_id, new_device_id)

    response = await client.post(f"/v1/tickets/{ticket_id}/restore", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body["ticket_id"] == str(ticket_id)
    assert body["state"] == "issued"


async def test_restore_ticket_no_auth(client):
    response = await client.post(f"/v1/tickets/{uuid.uuid4()}/restore")

    assert response.status_code == 401


async def test_restore_ticket_not_found(client, make_auth_headers):
    user_id = uuid.uuid4()
    device_id = uuid.uuid4()
    headers = make_auth_headers(user_id, device_id)

    response = await client.post(f"/v1/tickets/{uuid.uuid4()}/restore", headers=headers)

    assert response.status_code == 404
