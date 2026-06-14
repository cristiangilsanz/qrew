import math
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum

from sqlalchemy.ext.asyncio import AsyncSession

from com.qode.qrew.v1.ticketing.models.projections import DeviceContext, EventVenueContext
from com.qode.qrew.v1.ticketing.models.ticket import Ticket, TicketState
from com.qode.qrew.v1.ticketing.settings import settings

_EARTH_RADIUS_M = 6_371_000.0


class DenialReason(StrEnum):
    state = "state"
    reassertion = "reassertion"
    attestation = "attestation"
    geofence = "geofence"
    not_found = "not_found"
    not_owner = "not_owner"


@dataclass(frozen=True)
class GateInputs:
    ticket: Ticket
    event_ctx: EventVenueContext
    device_ctx: DeviceContext


def haversine_metres(*, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    )
    return float(2 * _EARTH_RADIUS_M * math.asin(math.sqrt(a)))


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
        return DenialReason.attestation
    return GateInputs(ticket=ticket, event_ctx=event_ctx, device_ctx=device_ctx)


def evaluate_gate(
    inputs: GateInputs,
    *,
    last_asserted_at: datetime | None,
    latitude: float,
    longitude: float,
    now: datetime,
) -> DenialReason | None:
    if inputs.ticket.state not in {TicketState.issued, TicketState.entry_pending}:
        return DenialReason.state
    if last_asserted_at is None:
        return DenialReason.reassertion
    la = last_asserted_at
    if la.tzinfo is None:
        la = la.replace(tzinfo=UTC)
    if now - la > timedelta(seconds=settings.ticket_qr_reassert_window_seconds):
        return DenialReason.reassertion
    if inputs.device_ctx.revoked_at is not None:
        return DenialReason.attestation
    if inputs.device_ctx.attested_at is None:
        return DenialReason.attestation
    attested = inputs.device_ctx.attested_at
    if attested.tzinfo is None:
        attested = attested.replace(tzinfo=UTC)
    if now - attested > timedelta(hours=settings.ticket_qr_attestation_max_age_hours):
        return DenialReason.attestation
    if event_ctx := inputs.event_ctx:
        if event_ctx.latitude is None or event_ctx.longitude is None or event_ctx.geofence_radius_m is None:  # type: ignore[reportUnnecessaryComparison]
            return DenialReason.geofence
        distance = haversine_metres(
            lat1=latitude,
            lon1=longitude,
            lat2=float(event_ctx.latitude),
            lon2=float(event_ctx.longitude),
        )
        if distance > event_ctx.geofence_radius_m:
            return DenialReason.geofence
    return None


__all__ = [
    "DenialReason",
    "GateInputs",
    "evaluate_gate",
    "haversine_metres",
    "load_inputs",
]
