import uuid

import pytest
from sqlalchemy import text

pytestmark = [pytest.mark.integration, pytest.mark.asyncio(loop_scope="session")]

_INTERNAL_HEADERS = {"X-Internal-Key": "test-internal-key"}


async def _seed_ticket(
    session_factory, *, state: str, ticket_id: uuid.UUID | None = None
) -> uuid.UUID:
    ticket_id = ticket_id or uuid.uuid4()
    async with session_factory() as session, session.begin():
        await session.execute(
            text("""
                INSERT INTO ticketing.tickets
                    (id, reservation_id, event_id, ticket_type_id, owner_user_id, state)
                VALUES (:id, :res_id, :ev_id, :tt_id, :owner_id, :state)
            """),
            {
                "id": ticket_id,
                "res_id": uuid.uuid4(),
                "ev_id": uuid.uuid4(),
                "tt_id": uuid.uuid4(),
                "owner_id": uuid.uuid4(),
                "state": state,
            },
        )
    return ticket_id


async def test_use_ticket_success(client, test_session_factory):
    ticket_id = await _seed_ticket(test_session_factory, state="scanning")

    response = await client.post(
        f"/v1/admission/{ticket_id}/use",
        json={"actor_id": str(uuid.uuid4())},
        headers=_INTERNAL_HEADERS,
    )

    assert response.status_code == 204


async def test_use_ticket_idempotent_already_used(client, test_session_factory):
    ticket_id = await _seed_ticket(test_session_factory, state="redeemed")

    response = await client.post(
        f"/v1/admission/{ticket_id}/use",
        json={"actor_id": str(uuid.uuid4())},
        headers=_INTERNAL_HEADERS,
    )

    assert response.status_code == 204


async def test_use_ticket_not_found(client):
    response = await client.post(
        f"/v1/admission/{uuid.uuid4()}/use",
        json={"actor_id": str(uuid.uuid4())},
        headers=_INTERNAL_HEADERS,
    )

    assert response.status_code == 404


async def test_use_ticket_no_auth(client):
    response = await client.post(
        f"/v1/admission/{uuid.uuid4()}/use",
        json={"actor_id": str(uuid.uuid4())},
    )

    assert response.status_code == 401
