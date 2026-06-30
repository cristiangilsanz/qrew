import hashlib
import json
import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from com.qode.qrew.v1.audit.models.event import AuditAction, AuditEvent


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
    ip_address: str | None,
    device_fingerprint_hash: str | None,
    user_agent: str | None,
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
        ip_address=ip_address,
        device_fingerprint_hash=device_fingerprint_hash,
        user_agent=user_agent,
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

    async def has_genesis(self) -> bool:
        result = await self._session.execute(
            select(AuditEvent.id).where(AuditEvent.action == AuditAction.GENESIS).limit(1)
        )
        return result.scalar_one_or_none() is not None

    async def get_all_ordered(self) -> list[AuditEvent]:
        result = await self._session.execute(
            select(AuditEvent).order_by(AuditEvent.created_at.asc(), AuditEvent.id.asc())
        )
        return list(result.scalars().all())
