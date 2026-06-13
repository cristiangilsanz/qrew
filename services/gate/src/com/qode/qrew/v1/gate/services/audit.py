import uuid
from datetime import UTC, datetime

import structlog
from sqlalchemy import text

from com.qode.qrew.v1.gate.core.infra.database import AsyncSessionLocal
from com.qode.qrew.v1.gate.repositories.audit import AuditRepository, build_event

logger = structlog.get_logger(__name__)

ADVISORY_LOCK = "SELECT pg_advisory_xact_lock(hashtext('audit_events'))"


class AuditService:
    async def record(
        self,
        action: str,
        actor_id: uuid.UUID | None = None,
        entity_type: str | None = None,
        entity_id: str | None = None,
        payload: dict[str, object] | None = None,
    ) -> None:
        now = datetime.now(UTC)
        async with AsyncSessionLocal() as session, session.begin():
            await session.execute(text(ADVISORY_LOCK))
            repo = AuditRepository(session)
            prev_hash = await repo.get_last_hash()
            event = build_event(
                action=action,
                actor_id=actor_id,
                entity_type=entity_type,
                entity_id=entity_id,
                payload=payload or {},
                created_at=now,
                prev_hash=prev_hash,
            )
            await repo.insert(event)
        await logger.ainfo(
            "audit_recorded",
            action=action,
            actor_id=str(actor_id) if actor_id else None,
        )
