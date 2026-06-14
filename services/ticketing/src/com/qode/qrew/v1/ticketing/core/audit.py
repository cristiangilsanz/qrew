import hashlib
import uuid
from datetime import UTC, datetime
from typing import Any

from com.qode.qrew.v1.ticketing.core.infra.database import AsyncSessionLocal


class AuditService:
    async def record(
        self,
        *,
        action: str,
        actor_id: uuid.UUID | None = None,
        entity_type: str | None = None,
        entity_id: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> None:
        from com.qode.qrew.v1.ticketing.models.audit import AuditEvent

        event_id = uuid.uuid4()
        now = datetime.now(UTC)
        raw = f"{event_id}{action}{actor_id}{entity_type}{entity_id}{now.isoformat()}"
        hash_bytes = hashlib.sha256(raw.encode()).digest()
        event = AuditEvent(
            id=event_id,
            action=str(action),
            actor_id=actor_id,
            entity_type=entity_type,
            entity_id=entity_id,
            payload=payload or {},
            occurred_at=now,
            hash=hash_bytes,
        )
        async with AsyncSessionLocal() as session, session.begin():
            session.add(event)
