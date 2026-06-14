import hashlib
import json
import uuid
from datetime import UTC, datetime
from typing import Any

import structlog

from com.qode.qrew.v1.sales.core.infra.database import AsyncSessionLocal
from com.qode.qrew.v1.sales.models.audit import AuditEvent

logger = structlog.get_logger(__name__)


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
        payload = payload or {}
        raw = json.dumps(
            {
                "action": action,
                "actor_id": str(actor_id) if actor_id else None,
                "entity_type": entity_type,
                "entity_id": entity_id,
                "payload": payload,
                "occurred_at": datetime.now(UTC).isoformat(),
            },
            sort_keys=True,
        ).encode()
        digest = hashlib.sha256(raw).digest()
        event = AuditEvent(
            action=action,
            actor_id=actor_id,
            entity_type=entity_type,
            entity_id=entity_id,
            payload=payload,
            hash=digest,
        )
        try:
            async with AsyncSessionLocal() as session:
                session.add(event)
                await session.commit()
        except Exception as exc:
            await logger.awarning("audit.write_failed", action=action, error=repr(exc))
