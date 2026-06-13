import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, LargeBinary, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from com.qode.qrew.v1.gate.core.infra.database import Base


class AuditAction(enum.StrEnum):
    GENESIS = "genesis"
    SCANNER_CREATED = "scanner_created"
    SCANNER_ROTATED = "scanner_rotated"
    SCANNER_DEACTIVATED = "scanner_deactivated"
    SCANNER_REFRESH_FAILED = "scanner_refresh_failed"
    ENTRY_VALIDATED = "entry_validated"
    ENTRY_REJECTED = "entry_rejected"


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
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    prev_hash: Mapped[bytes | None] = mapped_column(LargeBinary(32), nullable=True)
    hash: Mapped[bytes] = mapped_column(LargeBinary(32), nullable=False)
