import time
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timezone
from enum import StrEnum
from typing import Any

import jwt
import redis.asyncio as aioredis
import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from com.qode.qrew.v1.service.core.auth import jwt_keys
from com.qode.qrew.v1.service.core.locking import redlock
from com.qode.qrew.v1.service.core.locking.errors import LockUnavailableError
from com.qode.qrew.v1.service.core.observability import traced
from com.qode.qrew.v1.service.core.ws import publish as ws_publish
from com.qode.qrew.v1.service.realtime.entry_channel import entry_channel_key
from com.qode.qrew.v1.service.models.audit.audit import AuditAction
from com.qode.qrew.v1.service.models.scanner.scanner import Scanner
from com.qode.qrew.v1.service.models.ticket import Ticket, TicketState
from com.qode.qrew.v1.service.services.audit import AuditService
from com.qode.qrew.v1.service.services.ticket import (
    TicketTransitionError,
    transition_ticket,
)
from com.qode.qrew.v1.service.settings import settings

logger = structlog.get_logger(__name__)

_REPLAY_PREFIX = "entry:jti"


class EntryReason(StrEnum):
    """Typed reasons returned alongside `allowed=false`."""

    signature = "signature"
    audience = "audience"
    expired = "expired"
    wrong_event = "wrong_event"
    wrong_venue = "wrong_venue"
    replay = "replay"
    not_found = "not_found"
    wrong_owner = "wrong_owner"
    state = "state"
    busy = "busy"


@dataclass(frozen=True)
class EntryOutcome:
    allowed: bool
    reason: EntryReason | None
    ticket_id: uuid.UUID | None
    holder_user_id: uuid.UUID | None
    scanned_at: datetime


def _now() -> datetime:
    return datetime.now(UTC)


@traced("entry.validate")
async def validate_entry(
    session: AsyncSession,
    redis: aioredis.Redis,  # type: ignore[type-arg]
    *,
    ticket_jwt: str,
    scanner: Scanner,
    scanner_event_id: uuid.UUID | None,
    scanner_venue_id: uuid.UUID,
    audit: AuditService,
) -> EntryOutcome:
    """Run the seven-step gate. Every outcome writes one audit row."""
    started_at_ms = time.monotonic() * 1000
    decision = await _evaluate(
        session=session,
        redis=redis,
        ticket_jwt=ticket_jwt,
        scanner=scanner,
        scanner_event_id=scanner_event_id,
        scanner_venue_id=scanner_venue_id,
        audit=audit,
    )
    latency_ms = int(time.monotonic() * 1000 - started_at_ms)
    await logger.ainfo(
        "entry.scan.outcome",
        reason=decision.reason.value if decision.reason else "ok",
        ticket_id=str(decision.ticket_id) if decision.ticket_id else None,
        event_id=str(scanner_event_id) if scanner_event_id else None,
        scanner_id=str(scanner.id),
        latency_ms=latency_ms,
    )
    return decision


async def _evaluate(
    *,
    session: AsyncSession,
    redis: aioredis.Redis,  # type: ignore[type-arg]
    ticket_jwt: str,
    scanner: Scanner,
    scanner_event_id: uuid.UUID | None,
    scanner_venue_id: uuid.UUID,
    audit: AuditService,
) -> EntryOutcome:
    try:
        header = jwt.get_unverified_header(ticket_jwt)
        kid = header.get("kid")
        public_pem = (
            jwt_keys._KEYS[jwt_keys.TICKET_QR].verifiers.get(kid)  # pyright: ignore[reportPrivateUsage]
            if isinstance(kid, str)
            else None
        )
        if public_pem is None:
            raise jwt.InvalidTokenError("Unknown signing key")
        payload = jwt.decode(
            ticket_jwt,
            public_pem,
            algorithms=["ES256"],
            audience=settings.ticket_qr_audience,
        )
    except jwt.ExpiredSignatureError:
        await _audit_reject(audit, scanner.id, None, EntryReason.expired)
        return _denied(EntryReason.expired)
    except jwt.InvalidAudienceError:
        await _audit_reject(audit, scanner.id, None, EntryReason.audience)
        return _denied(EntryReason.audience)
    except jwt.InvalidTokenError:
        await _audit_reject(audit, scanner.id, None, EntryReason.signature)
        return _denied(EntryReason.signature)

    ticket_id_raw = payload.get("ticket_id")
    event_id_raw = payload.get("event_id")
    venue_id_raw = payload.get("venue_id")
    jti = payload.get("jti")
    exp = payload.get("exp")
    if not (
        isinstance(ticket_id_raw, str)
        and isinstance(event_id_raw, str)
        and isinstance(venue_id_raw, str)
        and isinstance(jti, str)
        and isinstance(exp, int)
    ):
        await _audit_reject(audit, scanner.id, None, EntryReason.signature)
        return _denied(EntryReason.signature)

    try:
        ticket_id = uuid.UUID(ticket_id_raw)
        event_id = uuid.UUID(event_id_raw)
        venue_id = uuid.UUID(venue_id_raw)
    except ValueError:
        await _audit_reject(audit, scanner.id, None, EntryReason.signature)
        return _denied(EntryReason.signature)

    if scanner_event_id is not None and scanner_event_id != event_id:
        await _audit_reject(
            audit, scanner.id, ticket_id, EntryReason.wrong_event, event_id=event_id
        )
        return _denied(EntryReason.wrong_event, ticket_id=ticket_id)
    if scanner_venue_id != venue_id:
        await _audit_reject(
            audit, scanner.id, ticket_id, EntryReason.wrong_venue, event_id=event_id
        )
        return _denied(EntryReason.wrong_venue, ticket_id=ticket_id)

    now_unix = int(_now().timestamp())
    remaining_ttl = max(exp - now_unix, 0) + settings.entry_replay_grace_seconds
    claimed = await redis.set(  # type: ignore[misc]
        f"{_REPLAY_PREFIX}:{jti}",
        str(ticket_id),
        ex=remaining_ttl,
        nx=True,
    )
    if not claimed:
        await _audit_reject(
            audit, scanner.id, ticket_id, EntryReason.replay, event_id=event_id
        )
        return _denied(EntryReason.replay, ticket_id=ticket_id)

    ticket = await session.get(Ticket, ticket_id)
    if ticket is None:
        await _audit_reject(
            audit, scanner.id, ticket_id, EntryReason.not_found, event_id=event_id
        )
        return _denied(EntryReason.not_found, ticket_id=ticket_id)
    if ticket.event_id != event_id:
        await _audit_reject(
            audit, scanner.id, ticket_id, EntryReason.wrong_owner, event_id=event_id
        )
        return _denied(EntryReason.wrong_owner, ticket_id=ticket_id)
    if ticket.state not in {TicketState.issued, TicketState.entry_pending}:
        await _audit_reject(
            audit,
            scanner.id,
            ticket_id,
            EntryReason.state,
            extra={"current_state": ticket.state.value},
            event_id=event_id,
        )
        return _denied(EntryReason.state, ticket_id=ticket_id)

    try:
        async with redlock(f"ticket:{ticket_id}:entry", ttl_seconds=10):
            await transition_ticket(
                session,
                ticket_id=ticket_id,
                to_state=TicketState.used,
                reason="entry_validated",
                actor_id=scanner.id,
                audit=audit,
            )
    except (LockUnavailableError, TicketTransitionError):
        await _audit_reject(
            audit, scanner.id, ticket_id, EntryReason.busy, event_id=event_id
        )
        return _denied(EntryReason.busy, ticket_id=ticket_id)

    await audit.record(
        action=AuditAction.ENTRY_VALIDATED,
        actor_id=scanner.id,
        entity_type="ticket",
        entity_id=str(ticket_id),
        payload={
            "event_id": str(event_id),
            "venue_id": str(venue_id),
            "scanner_id": str(scanner.id),
        },
    )
    try:
        await ws_publish(
            entry_channel_key(str(event_id)),
            {
                "type": "entry.validated",
                "ticket_id": str(ticket_id),
                "scanner_id": str(scanner.id),
                "scanned_at": _now().isoformat(),
            },
        )
    except Exception:
        await logger.awarning("entry_ws_publish_failed", event_id=str(event_id))
    return EntryOutcome(
        allowed=True,
        reason=None,
        ticket_id=ticket_id,
        holder_user_id=ticket.owner_user_id,
        scanned_at=_now(),
    )


def _denied(reason: EntryReason, *, ticket_id: uuid.UUID | None = None) -> EntryOutcome:
    return EntryOutcome(
        allowed=False,
        reason=reason,
        ticket_id=ticket_id,
        holder_user_id=None,
        scanned_at=datetime.now(timezone.utc),
    )


async def _audit_reject(
    audit: AuditService,
    scanner_id: uuid.UUID,
    ticket_id: uuid.UUID | None,
    reason: EntryReason,
    *,
    extra: dict[str, Any] | None = None,
    event_id: uuid.UUID | None = None,
) -> None:
    payload: dict[str, Any] = {"reason": reason.value, "scanner_id": str(scanner_id)}
    if extra:
        payload.update(extra)
    if event_id is not None:
        payload["event_id"] = str(event_id)
    try:
        await audit.record(
            action=AuditAction.ENTRY_REJECTED,
            actor_id=scanner_id,
            entity_type="ticket",
            entity_id=str(ticket_id) if ticket_id else None,
            payload=payload,
        )
    except Exception:
        await logger.awarning("audit_write_failed", action=AuditAction.ENTRY_REJECTED)
    if event_id is not None:
        try:
            await ws_publish(
                entry_channel_key(str(event_id)),
                {
                    "type": "entry.rejected",
                    "reason": reason.value,
                    "scanned_at": _now().isoformat(),
                },
            )
        except Exception:
            await logger.awarning("entry_ws_publish_failed", event_id=str(event_id))
