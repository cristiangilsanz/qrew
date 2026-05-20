import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

import structlog
from sqlalchemy import text

from com.qode.qrew.v1.service.core.database import AsyncSessionLocal
from com.qode.qrew.v1.service.models.audit import AuditAction
from com.qode.qrew.v1.service.repositories.audit import (
    AuditRepository,
    build_event,
    compute_hash,
    event_to_hashable,
)

logger = structlog.get_logger(__name__)

_ADVISORY_LOCK = "SELECT pg_advisory_xact_lock(hashtext('audit_events'))"


@dataclass
class ChainVerificationResult:
    valid: bool
    event_count: int
    tampered_ids: list[str]


class AuditService:
    """Append-only audit log with SHA-256 Merkle hash chain.

    Uses its own session (independent of the caller's transaction) so that audit
    events are always committed, even when the main transaction rolls back.
    The advisory lock serialises all inserts so the hash chain is never forked.
    """

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
        now = datetime.now(UTC)
        async with AsyncSessionLocal() as session, session.begin():
            await session.execute(text(_ADVISORY_LOCK))
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
        """Write the genesis record on first boot. Idempotent."""
        async with AsyncSessionLocal() as session, session.begin():
            await session.execute(text(_ADVISORY_LOCK))
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

    async def verify_chain(self) -> ChainVerificationResult:
        """Recompute every hash from genesis and return tampered IDs."""
        async with AsyncSessionLocal() as session:
            repo = AuditRepository(session)
            events = await repo.get_all_ordered()

        prev_hash: bytes | None = None
        tampered: list[str] = []

        for event in events:
            expected = compute_hash(prev_hash, event_to_hashable(event))
            if event.hash != expected:
                tampered.append(str(event.id))
            # always advance using the stored hash so a single tampered row
            # does not cascade false positives to every subsequent event
            prev_hash = event.hash

        return ChainVerificationResult(
            valid=len(tampered) == 0,
            event_count=len(events),
            tampered_ids=tampered,
        )
