import uuid
from datetime import UTC, datetime

import structlog
from sqlalchemy import DateTime, LargeBinary, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from com.qode.qrew.v1.catalog.core.infra.database import AsyncSessionLocal, Base

logger = structlog.get_logger(__name__)


class AuditEvent(Base):
    __tablename__ = "audit_events"
    __table_args__ = {"schema": "audit"}

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    actor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
    action: Mapped[str] = mapped_column(String(64), index=True)
    entity_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    entity_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    device_fingerprint_hash: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    payload: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), index=True
    )
    prev_hash: Mapped[bytes | None] = mapped_column(LargeBinary(32), nullable=True)
    hash: Mapped[bytes] = mapped_column(LargeBinary(32), nullable=False)


class AuditService:
    """Simplified audit writer — appends to audit.audit_events without hash chain."""

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
        import hashlib

        now = datetime.now(UTC)
        event_id = uuid.uuid4()
        raw = f"{event_id}{action}{actor_id}{entity_type}{entity_id}{now.isoformat()}"
        hash_bytes = hashlib.sha256(raw.encode()).digest()
        event = AuditEvent(
            id=event_id,
            actor_id=actor_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            ip_address=ip_address,
            device_fingerprint_hash=device_fingerprint_hash,
            user_agent=user_agent,
            payload=payload or {},
            created_at=now,
            prev_hash=None,
            hash=hash_bytes,
        )
        try:
            async with AsyncSessionLocal() as session, session.begin():
                session.add(event)
        except Exception as exc:
            await logger.awarning("audit_write_failed", action=action, error=repr(exc))
