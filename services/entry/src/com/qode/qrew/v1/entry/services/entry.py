import time
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timezone
from enum import StrEnum
from typing import Any

import httpx
import jwt
import redis.asyncio as aioredis
import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from com.qode.qrew.v1.entry.core import principals as jwt_keys
from locking import LockUnavailableError, redlock
from observability import traced
from com.qode.qrew.v1.entry.models.audit import AuditAction
from com.qode.qrew.v1.entry.models.scanner import Scanner
from com.qode.qrew.v1.entry.models.ticket_context import TicketState
from com.qode.qrew.v1.entry.repositories.ticket_context import TicketContextRepository
from com.qode.qrew.v1.entry.services.audit import AuditService
from com.qode.qrew.v1.entry.core.config import settings

logger = structlog.get_logger(__name__)

_REPLAY_PREFIX = "entry:jti"
_ENTRY_CHANNEL_PATTERN = "entry.{event_id}"


def _entry_channel_key(event_id: str) -> str:
    return _ENTRY_CHANNEL_PATTERN.format(event_id=event_id)


class EntryReason(StrEnum):
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
        verifiers = jwt_keys.get_verifiers(jwt_keys.TICKET_QR)
        public_pem = verifiers.get(kid) if isinstance(kid, str) else None
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
        await _audit_reject(audit, scanner.id, ticket_id, EntryReason.wrong_event, event_id=event_id)
        return _denied(EntryReason.wrong_event, ticket_id=ticket_id)
    if scanner_venue_id != venue_id:
        await _audit_reject(audit, scanner.id, ticket_id, EntryReason.wrong_venue, event_id=event_id)
        return _denied(EntryReason.wrong_venue, ticket_id=ticket_id)

    now_unix = int(_now().timestamp())
    remaining_ttl = max(exp - now_unix, 0) + settings.entry_replay_grace_seconds
    claimed = await redis.set(  # type: ignore[misc]
        f"{_REPLAY_PREFIX}:{jti}", str(ticket_id), ex=remaining_ttl, nx=True
    )
    if not claimed:
        await _audit_reject(audit, scanner.id, ticket_id, EntryReason.replay, event_id=event_id)
        return _denied(EntryReason.replay, ticket_id=ticket_id)

    tc_repo = TicketContextRepository(session)
    ticket_ctx = await tc_repo.get(ticket_id)
    if ticket_ctx is None:
        await _audit_reject(audit, scanner.id, ticket_id, EntryReason.not_found, event_id=event_id)
        return _denied(EntryReason.not_found, ticket_id=ticket_id)
    if ticket_ctx.event_id != event_id:
        await _audit_reject(audit, scanner.id, ticket_id, EntryReason.wrong_owner, event_id=event_id)
        return _denied(EntryReason.wrong_owner, ticket_id=ticket_id)

    valid_states = {TicketState.issued.value, TicketState.entry_pending.value}
    if ticket_ctx.state not in valid_states:
        await _audit_reject(
            audit,
            scanner.id,
            ticket_id,
            EntryReason.state,
            extra={"current_state": ticket_ctx.state},
            event_id=event_id,
        )
        return _denied(EntryReason.state, ticket_id=ticket_id)

    try:
        async with redlock(f"ticket:{ticket_id}:entry", redis_url=settings.redis_url, ttl_seconds=10):
            await _call_monolith_use(ticket_id, scanner.id)
    except LockUnavailableError:
        await _audit_reject(audit, scanner.id, ticket_id, EntryReason.busy, event_id=event_id)
        return _denied(EntryReason.busy, ticket_id=ticket_id)
    except _MonolithUseError:
        await _audit_reject(audit, scanner.id, ticket_id, EntryReason.busy, event_id=event_id)
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
        from broker.publisher import publish as _nats_publish  # type: ignore[import-not-found]
        from contracts.envelope import EventEnvelope  # type: ignore[import-not-found]
        from datetime import UTC as _UTC, datetime as _dt

        _channel = _entry_channel_key(str(event_id))
        _payload = {
            "type": "entry.validated",
            "ticket_id": str(ticket_id),
            "scanner_id": str(scanner.id),
            "scanned_at": _now().isoformat(),
        }
        await _nats_publish(
            "ws.fanout.v1",
            EventEnvelope(
                occurred_at=_dt.now(_UTC),
                aggregate_type="ws_fanout",
                aggregate_id=_channel,
                data={"channel": _channel, "payload": _payload},
            ),
        )
    except Exception:
        await logger.awarning("entry_ws_publish_failed", event_id=str(event_id))

    return EntryOutcome(
        allowed=True,
        reason=None,
        ticket_id=ticket_id,
        holder_user_id=ticket_ctx.owner_user_id,
        scanned_at=_now(),
    )


class _MonolithUseError(Exception):
    pass


async def _call_monolith_use(ticket_id: uuid.UUID, scanner_id: uuid.UUID) -> None:
    """Forwards a ticket use request to the downstream ticketing service."""
    url = f"{settings.ticketing_url}/v1/_internal/tickets/{ticket_id}/use"
    async with httpx.AsyncClient(timeout=5.0) as client:
        resp = await client.post(
            url,
            headers={"X-Internal-Key": settings.internal_api_key},
            json={"actor_id": str(scanner_id)},
        )
    if resp.status_code == 409:
        # Already used — idempotent
        return
    if resp.status_code not in {200, 204}:
        raise _MonolithUseError(f"monolith returned {resp.status_code}")


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
            from broker.publisher import publish as _nats_publish  # type: ignore[import-not-found]
            from contracts.envelope import EventEnvelope  # type: ignore[import-not-found]
            from datetime import UTC as _UTC, datetime as _dt

            _channel = _entry_channel_key(str(event_id))
            _payload = {
                "type": "entry.rejected",
                "reason": reason.value,
                "scanned_at": _now().isoformat(),
            }
            await _nats_publish(
                "ws.fanout.v1",
                EventEnvelope(
                    occurred_at=_dt.now(_UTC),
                    aggregate_type="ws_fanout",
                    aggregate_id=_channel,
                    data={"channel": _channel, "payload": _payload},
                ),
            )
        except Exception:
            await logger.awarning("entry_ws_publish_failed", event_id=str(event_id))
