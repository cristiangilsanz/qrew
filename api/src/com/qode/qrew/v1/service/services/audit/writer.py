import uuid
from datetime import UTC, datetime

import structlog
from sqlalchemy import text

from com.qode.qrew.v1.service.core.infra.database import AsyncSessionLocal
from com.qode.qrew.v1.service.models.audit.audit import AuditAction, AuditEvent
from com.qode.qrew.v1.service.repositories.audit.audit import (
    AuditRepository,
    build_event,
)

logger = structlog.get_logger(__name__)

ADVISORY_LOCK = "SELECT pg_advisory_xact_lock(hashtext('audit_events'))"


class AuditService:
    """Append-only audit log writer."""

    async def record(
        self,
        action: str,
        actor_id: uuid.UUID | None = None,
        entity_type: str | None = None,
        entity_id: str | None = None,
        ip_address: str | None = None,
        device_fingerprint_hash: str | None = None,
        user_agent: str | None = None,
        payload: dict[str, object] | None = None,
    ) -> None:
        """Append a new audit event chained to the previous one."""
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
                ip_address=ip_address,
                device_fingerprint_hash=device_fingerprint_hash,
                user_agent=user_agent,
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

    async def ensure_genesis(self) -> None:
        """Write the genesis record once at startup."""
        async with AsyncSessionLocal() as session, session.begin():
            await session.execute(text(ADVISORY_LOCK))
            repo = AuditRepository(session)
            if await repo.has_genesis():
                return
            event = build_event(
                action=AuditAction.GENESIS,
                actor_id=None,
                entity_type="system",
                entity_id=None,
                ip_address=None,
                device_fingerprint_hash=None,
                user_agent=None,
                payload={"message": "Audit chain genesis"},
                created_at=datetime.now(UTC),
                prev_hash=None,
            )
            await repo.insert(event)
        await logger.ainfo("audit_genesis_created")

    async def get_recent_login_events(
        self, user_id: uuid.UUID, limit: int = 5
    ) -> list[AuditEvent]:
        """List the most recent successful logins for a user."""
        async with AsyncSessionLocal() as session:
            repo = AuditRepository(session)
            return await repo.get_recent_login_events(user_id, limit)
