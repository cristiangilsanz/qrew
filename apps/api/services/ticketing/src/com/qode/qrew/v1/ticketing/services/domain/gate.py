# decides whether a ticket may mint a qr at the gate
import math
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum

from sqlalchemy.ext.asyncio import AsyncSession

from com.qode.qrew.v1.ticketing.models.projections import DeviceContext, EventVenueContext
from com.qode.qrew.v1.ticketing.models.ticket import Ticket, TicketState
from com.qode.qrew.v1.ticketing.core.config import settings

_EARTH_RADIUS_M = 6_371_000.0


_QR_WINDOW_HOURS_BEFORE = 5


class DenialReason(StrEnum):
    state = "state"
    reassertion = "reassertion"
    attestation = "attestation"
    device_binding = "device_binding"
    geofence = "geofence"
    time_window = "time_window"
    not_found = "not_found"
    not_owner = "not_owner"


@dataclass(frozen=True)
class GateInputs:
    ticket: Ticket
    event_ctx: EventVenueContext
    device_ctx: DeviceContext


# computes the great circle distance between two coordinates in metres
def haversine_metres(*, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return float(2 * _EARTH_RADIUS_M * math.asin(math.sqrt(a)))


# loads the ticket event and device context a gate decision needs
async def load_inputs(
    session: AsyncSession,
    *,
    ticket_id: uuid.UUID,
    user_id: uuid.UUID,
    device_id: uuid.UUID,
) -> GateInputs | DenialReason:
    ticket = await session.get(Ticket, ticket_id)
    if ticket is None:
        return DenialReason.not_found
    if ticket.owner_user_id != user_id:
        return DenialReason.not_owner
    event_ctx = await session.get(EventVenueContext, ticket.event_id)
    if event_ctx is None:
        return DenialReason.not_found
    device_ctx = await session.get(DeviceContext, device_id)
    if device_ctx is None:
        if settings.ticket_qr_require_device_binding:
            return DenialReason.device_binding
        now = datetime.now(UTC)
        device_ctx = DeviceContext(
            device_id=device_id,
            user_id=user_id,
            attested_at=now,
            revoked_at=None,
            updated_at=now,
        )
    return GateInputs(ticket=ticket, event_ctx=event_ctx, device_ctx=device_ctx)


# checks the ticket state reassertion attestation geofence and time window
def evaluate_gate(
    inputs: GateInputs,
    *,
    last_asserted_at: datetime | None,
    latitude: float,
    longitude: float,
    now: datetime,
) -> DenialReason | None:
    if inputs.ticket.state not in {TicketState.issued, TicketState.scanning}:
        return DenialReason.state
    if settings.ticket_qr_require_reassertion:
        if last_asserted_at is None:
            return DenialReason.reassertion
        la = last_asserted_at
        if la.tzinfo is None:
            la = la.replace(tzinfo=UTC)
        if now - la > timedelta(seconds=settings.ticket_qr_reassert_window_seconds):
            return DenialReason.reassertion
    if settings.ticket_qr_require_device_binding:
        if inputs.device_ctx.revoked_at is not None:
            return DenialReason.device_binding
    if settings.ticket_qr_require_attestation:
        if inputs.device_ctx.attested_at is None:
            return DenialReason.attestation
        attested = inputs.device_ctx.attested_at
        if attested.tzinfo is None:
            attested = attested.replace(tzinfo=UTC)
        if now - attested > timedelta(hours=settings.ticket_qr_attestation_max_age_hours):
            return DenialReason.attestation
    event_ctx = inputs.event_ctx
    if settings.ticket_qr_require_geofence:
        if (
            event_ctx.latitude is None  # type: ignore[reportUnnecessaryComparison]
            or event_ctx.longitude is None  # type: ignore[reportUnnecessaryComparison]
            or event_ctx.geofence_radius_m is None  # type: ignore[reportUnnecessaryComparison]
        ):
            return DenialReason.geofence
        distance = haversine_metres(
            lat1=latitude,
            lon1=longitude,
            lat2=float(event_ctx.latitude),
            lon2=float(event_ctx.longitude),
        )
        if distance > event_ctx.geofence_radius_m:
            return DenialReason.geofence
    starts_at = event_ctx.starts_at
    ends_at = event_ctx.ends_at
    if starts_at is not None and ends_at is not None:
        if starts_at.tzinfo is None:
            starts_at = starts_at.replace(tzinfo=UTC)
        if ends_at.tzinfo is None:
            ends_at = ends_at.replace(tzinfo=UTC)
        earliest = starts_at - timedelta(hours=_QR_WINDOW_HOURS_BEFORE)
        if now < earliest or now > ends_at:
            return DenialReason.time_window
    return None


__all__ = [
    "DenialReason",
    "GateInputs",
    "_QR_WINDOW_HOURS_BEFORE",
    "evaluate_gate",
    "haversine_metres",
    "load_inputs",
]
