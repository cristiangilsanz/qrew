import uuid
from datetime import UTC, datetime, timedelta

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from com.qode.qrew.v1.ticketing.services.application.audit import AuditService
from com.qode.qrew.v1.ticketing.core.errors import DomainError
from com.qode.qrew.v1.ticketing.models.projections import DeviceContext
from com.qode.qrew.v1.ticketing.models.ticket import Ticket, TicketState
from com.qode.qrew.v1.ticketing.services.domain.tickets.lifecycle import transition_ticket
from com.qode.qrew.v1.ticketing.core.config import settings

logger = structlog.get_logger(__name__)

_TICKET_RESTORED = "TICKET_RESTORED_AFTER_REENROL"


class TicketRestoreError(DomainError):
    pass


async def restore_on_sale_ticket(
    db: AsyncSession,
    *,
    actor_id: uuid.UUID,
    ticket_id: uuid.UUID,
    session_device_id: uuid.UUID | None,
    last_asserted_at: datetime | None,
    audit: AuditService,
) -> Ticket:
    ticket = await db.get(Ticket, ticket_id)
    if ticket is None or ticket.owner_user_id != actor_id:
        raise TicketRestoreError("Ticket not found", field="ticket_id")
    if ticket.state != TicketState.on_sale:
        raise TicketRestoreError("Ticket is not on sale", field="state")
    if session_device_id is None:
        raise TicketRestoreError(
            "Restore requires an authenticated device session", field="device_id"
        )
    if ticket.bound_device_id is not None and ticket.bound_device_id == session_device_id:
        raise TicketRestoreError("Re-enrol onto a new device before restoring", field="device_id")
    now = datetime.now(UTC)
    if last_asserted_at is None:
        raise TicketRestoreError("Fresh passkey reassertion is required", field="reassertion")
    la = last_asserted_at
    if la.tzinfo is None:
        la = la.replace(tzinfo=UTC)
    window = timedelta(seconds=settings.ticket_qr_reassert_window_seconds)
    if now - la > window:
        raise TicketRestoreError("Fresh passkey reassertion is required", field="reassertion")
    device = await db.get(DeviceContext, session_device_id)
    if device is None or device.user_id != actor_id:
        raise TicketRestoreError("Device not found", field="device_id")
    if device.revoked_at is not None:
        raise TicketRestoreError("Device is revoked", field="device_id")
    if device.attested_at is None:
        raise TicketRestoreError("Device attestation is required", field="attestation")
    attested = device.attested_at
    if attested.tzinfo is None:
        attested = attested.replace(tzinfo=UTC)
    if now - attested > timedelta(hours=settings.ticket_qr_attestation_max_age_hours):
        raise TicketRestoreError("Device attestation is stale", field="attestation")
    previous_device = ticket.bound_device_id
    await transition_ticket(
        db,
        ticket_id=ticket.id,
        to_state=TicketState.issued,
        reason="restore_after_reenrol",
        actor_id=actor_id,
        audit=audit,
    )
    ticket.bound_device_id = session_device_id
    await db.flush()
    try:
        await audit.record(
            action=_TICKET_RESTORED,
            actor_id=actor_id,
            entity_type="ticket",
            entity_id=str(ticket.id),
            payload={
                "previous_device_id": str(previous_device) if previous_device else None,
                "new_device_id": str(session_device_id),
            },
        )
    except Exception as exc:
        await logger.awarning("audit_write_failed", action=_TICKET_RESTORED, error=repr(exc))
    await _publish_restored(ticket, actor_id)
    return ticket


async def _publish_restored(ticket: Ticket, actor_id: uuid.UUID) -> None:
    try:
        from messaging.publisher import publish  # type: ignore[import-untyped]
        from contracts.messaging.envelope import EventEnvelope  # type: ignore[import-untyped]

        envelope = EventEnvelope(
            occurred_at=datetime.now(UTC),
            aggregate_type="ticket",
            aggregate_id=str(ticket.id),
            data={"ticket_id": str(ticket.id), "user_id": str(actor_id)},
        )
        await publish("ticketing.ticket.restored", envelope)
    except Exception as exc:
        await logger.awarning(
            "nats_publish_failed", subject="ticketing.ticket.restored", error=repr(exc)
        )
