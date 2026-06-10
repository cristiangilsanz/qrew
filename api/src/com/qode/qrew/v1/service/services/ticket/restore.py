import uuid
from datetime import UTC, datetime, timedelta

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from com.qode.qrew.v1.service.core.infra.errors import DomainError
from com.qode.qrew.v1.service.core.observability import traced
from com.qode.qrew.v1.service.core.outbox import publish_via_outbox
from com.qode.qrew.v1.service.models.audit.audit import AuditAction
from com.qode.qrew.v1.service.models.auth.session import Session
from com.qode.qrew.v1.service.models.device.device import Device
from com.qode.qrew.v1.service.models.ticket import Ticket, TicketState
from com.qode.qrew.v1.service.services.audit import AuditService
from com.qode.qrew.v1.service.services.ticket.transition import transition_ticket
from com.qode.qrew.v1.service.settings import settings

logger = structlog.get_logger(__name__)


class TicketRestoreError(DomainError):
    """Raised when a frozen ticket cannot be restored."""


@traced("ticket.restore")
async def restore_frozen_ticket(
    db: AsyncSession,
    *,
    actor_id: uuid.UUID,
    ticket_id: uuid.UUID,
    auth_session: Session,
    audit: AuditService,
) -> Ticket:
    """Move a frozen ticket back to issued on a fresh, attested, different device."""
    ticket = await db.get(Ticket, ticket_id)
    if ticket is None or ticket.owner_user_id != actor_id:
        raise TicketRestoreError("Ticket not found", field="ticket_id")
    if ticket.state != TicketState.frozen:
        raise TicketRestoreError("Ticket is not frozen", field="state")
    device_id = auth_session.device_id
    if device_id is None:
        raise TicketRestoreError(
            "Restore requires an authenticated device session", field="device_id"
        )
    if ticket.bound_device_id is not None and ticket.bound_device_id == device_id:
        raise TicketRestoreError(
            "Re-enrol onto a new device before restoring", field="device_id"
        )
    last_asserted = auth_session.last_asserted_at
    now = datetime.now(UTC)
    if last_asserted is None:
        raise TicketRestoreError(
            "Fresh passkey reassertion is required", field="reassertion"
        )
    if last_asserted.tzinfo is None:
        last_asserted = last_asserted.replace(tzinfo=UTC)
    window = timedelta(seconds=settings.ticket_qr_reassert_window_seconds)
    if now - last_asserted > window:
        raise TicketRestoreError(
            "Fresh passkey reassertion is required", field="reassertion"
        )
    device = await db.get(Device, device_id)
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
    ticket.bound_device_id = device_id
    await db.flush()
    try:
        await audit.record(
            action=AuditAction.TICKET_RESTORED_AFTER_REENROL,
            actor_id=actor_id,
            entity_type="ticket",
            entity_id=str(ticket.id),
            payload={
                "previous_device_id": str(previous_device) if previous_device else None,
                "new_device_id": str(device_id),
            },
        )
    except Exception:
        await logger.awarning(
            "audit_write_failed", action=AuditAction.TICKET_RESTORED_AFTER_REENROL
        )
    try:
        await publish_via_outbox(
            db,
            aggregate_type="ticket",
            aggregate_id=str(ticket.id),
            job_name="notifications.ticket_restored",
            payload={"ticket_id": str(ticket.id), "user_id": str(actor_id)},
        )
    except Exception:
        await logger.awarning("outbox_publish_failed")
    return ticket
