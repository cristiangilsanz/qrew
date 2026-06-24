import uuid
from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from com.qode.qrew.v1.audit.models.event import AuditAction, AuditEvent
from com.qode.qrew.v1.audit.repositories.audit import build_event

pytestmark = [pytest.mark.integration, pytest.mark.asyncio(loop_scope="session")]


def _make_chain(n: int, base_time: datetime | None = None) -> list[AuditEvent]:
    events: list[AuditEvent] = []
    prev_hash: bytes | None = None
    t = base_time or datetime(2024, 1, 1, tzinfo=UTC)
    for i in range(n):
        event = build_event(
            action=AuditAction.LOGIN,
            actor_id=uuid.uuid4(),
            entity_type="user",
            entity_id=str(uuid.uuid4()),
            ip_address=None,
            device_fingerprint_hash=None,
            user_agent=None,
            payload={},
            created_at=t + timedelta(seconds=i),
            prev_hash=prev_hash,
        )
        prev_hash = event.hash
        events.append(event)
    return events


async def _seed_chain(
    db: AsyncSession, n: int, base_time: datetime | None = None
) -> list[AuditEvent]:
    events = _make_chain(n, base_time=base_time)
    for event in events:
        db.add(event)
    await db.flush()
    await db.commit()
    return events


@pytest.mark.integration
async def test_verify_empty_chain(client: AsyncClient, internal_headers: dict[str, str]) -> None:
    response = await client.get("/v1/audit/chain/verify", headers=internal_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["valid"] is True
    assert body["event_count"] == 0
    assert body["tampered_ids"] == []


@pytest.mark.integration
async def test_verify_valid_chain(
    client: AsyncClient,
    db: AsyncSession,
    internal_headers: dict[str, str],
) -> None:
    await _seed_chain(db, 3, base_time=datetime(2024, 1, 2, tzinfo=UTC))
    response = await client.get("/v1/audit/chain/verify", headers=internal_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["valid"] is True
    assert body["event_count"] >= 3
    assert body["tampered_ids"] == []


@pytest.mark.integration
async def test_verify_tampered_chain(
    client: AsyncClient,
    db: AsyncSession,
    internal_headers: dict[str, str],
) -> None:
    events = await _seed_chain(db, 2, base_time=datetime(2024, 1, 3, tzinfo=UTC))
    # Corrupt the hash of the second event
    target_id = str(events[1].id)
    await db.execute(
        text("UPDATE audit.audit_events SET hash = :bad WHERE id = CAST(:id AS uuid)"),
        {"bad": b"\x00" * 32, "id": target_id},
    )
    await db.commit()

    response = await client.get("/v1/audit/chain/verify", headers=internal_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["valid"] is False
    assert target_id in body["tampered_ids"]


@pytest.mark.integration
async def test_verify_no_key(client: AsyncClient) -> None:
    response = await client.get("/v1/audit/chain/verify")
    assert response.status_code in (403, 422)


@pytest.mark.integration
async def test_verify_wrong_key(client: AsyncClient) -> None:
    response = await client.get("/v1/audit/chain/verify", headers={"X-Internal-Key": "wrong-key"})
    assert response.status_code == 403
