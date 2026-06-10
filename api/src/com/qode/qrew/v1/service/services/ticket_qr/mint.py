import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

import structlog

from com.qode.qrew.v1.service.core.auth import jwt_keys
from com.qode.qrew.v1.service.core.observability import traced
from com.qode.qrew.v1.service.models.audit.audit import AuditAction
from com.qode.qrew.v1.service.services.audit import AuditService
from com.qode.qrew.v1.service.services.ticket_qr.gate import GateInputs
from com.qode.qrew.v1.service.settings import settings

logger = structlog.get_logger(__name__)


@dataclass(frozen=True)
class MintedQr:
    jwt: str
    jti: str
    issued_at: datetime
    expires_at: datetime


def _sample_audit(rate: int) -> bool:
    if rate <= 1:
        return True
    return secrets.randbelow(rate) == 0


@traced("ticket_qr.mint")
async def mint_qr(
    *,
    inputs: GateInputs,
    user_id: uuid.UUID,
    device_id: uuid.UUID,
    audit: AuditService,
    now: datetime,
) -> MintedQr:
    """Mint a fresh short-lived QR JWT for an already-gated ticket."""
    if inputs.ticket.bound_device_id != device_id:
        inputs.ticket.bound_device_id = device_id
    jti = uuid.uuid4().hex
    exp = now + timedelta(seconds=settings.ticket_qr_ttl_seconds)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "ticket_id": str(inputs.ticket.id),
        "event_id": str(inputs.event.id),
        "venue_id": str(inputs.venue.id),
        "device_id": str(device_id),
        "jti": jti,
        "iat": now,
        "exp": exp,
        "aud": settings.ticket_qr_audience,
    }
    token = jwt_keys.sign(jwt_keys.TICKET_QR, payload)
    if _sample_audit(settings.ticket_qr_mint_audit_sample_rate):
        try:
            await audit.record(
                action=AuditAction.TICKET_QR_MINTED,
                actor_id=user_id,
                entity_type="ticket",
                entity_id=str(inputs.ticket.id),
                payload={"jti": jti, "device_id": str(device_id)},
            )
        except Exception:
            await logger.awarning(
                "audit_write_failed", action=AuditAction.TICKET_QR_MINTED
            )
    return MintedQr(jwt=token, jti=jti, issued_at=now, expires_at=exp)


async def record_denial(
    *,
    audit: AuditService,
    user_id: uuid.UUID,
    ticket_id: uuid.UUID,
    reason: str,
    device_id: uuid.UUID | None,
) -> None:
    try:
        await audit.record(
            action=AuditAction.TICKET_QR_DENIED,
            actor_id=user_id,
            entity_type="ticket",
            entity_id=str(ticket_id),
            payload={
                "reason": reason,
                "device_id": str(device_id) if device_id else None,
            },
        )
    except Exception:
        await logger.awarning("audit_write_failed", action=AuditAction.TICKET_QR_DENIED)


def utc_now() -> datetime:
    return datetime.now(UTC)
