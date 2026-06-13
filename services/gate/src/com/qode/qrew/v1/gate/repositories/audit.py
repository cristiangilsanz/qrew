import hashlib
import json
import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from com.qode.qrew.v1.gate.models.audit import AuditEvent


def _canonical_json(data: dict[str, object]) -> bytes:
    return json.dumps(data, sort_keys=True, default=str, separators=(",", ":")).encode()


def compute_hash(prev_hash: bytes | None, event_data: dict[str, object]) -> bytes:
    return hashlib.sha256((prev_hash or b"") + _canonical_json(event_data)).digest()


def event_to_hashable(event: AuditEvent) -> dict[str, object]:
    return {
        "id": str(event.id),
        "actor_id": str(event.actor_id) if event.actor_id else None,
        "action": event.action,
        "entity_type": event.entity_type,
        "entity_id": event.entity_id,
        "ip_address": event.ip_address,
        "device_fingerprint_hash": event.device_fingerprint_hash,
        "user_agent": event.user_agent,
        "payload": event.payload,
        "created_at": event.created_at.isoformat(),
    }


def build_event(
    action: str,
    actor_id: uuid.UUID | None,
    entity_type: str | None,
    entity_id: str | None,
    payload: dict[str, object],
    created_at: datetime,
    prev_hash: bytes | None,
) -> AuditEvent:
    event = AuditEvent(
        id=uuid.uuid4(),
        actor_id=actor_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        ip_address=None,
        device_fingerprint_hash=None,
        user_agent=None,
        payload=payload,
        created_at=created_at,
        prev_hash=prev_hash,
        hash=b"",
    )
    event.hash = compute_hash(prev_hash, event_to_hashable(event))
    return event


class AuditRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_last_hash(self) -> bytes | None:
        result = await self._session.execute(
            select(AuditEvent.hash)
            .order_by(AuditEvent.created_at.desc(), AuditEvent.id.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def insert(self, event: AuditEvent) -> AuditEvent:
        self._session.add(event)
        await self._session.flush()
        return event
