import math
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from com.qode.qrew.v1.service.models.auth.session import Session
from com.qode.qrew.v1.service.models.device.device import Device
from com.qode.qrew.v1.service.models.event import Event
from com.qode.qrew.v1.service.models.ticket import Ticket, TicketState
from com.qode.qrew.v1.service.models.venue import Venue
from com.qode.qrew.v1.service.settings import settings

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
    event: Event
    venue: Venue
    device: Device


def haversine_metres(*, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in metres between two WGS-84 points."""
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
    """Resolve the four aggregates the gate compares; or return a denial reason."""
    ticket = await session.get(Ticket, ticket_id)
    if ticket is None:
        return DenialReason.not_found
    if ticket.owner_user_id != user_id:
        return DenialReason.not_owner
    event = await session.get(Event, ticket.event_id)
    if event is None:
        return DenialReason.not_found
    venue = await session.get(Venue, event.venue_id)
    if venue is None:
        return DenialReason.not_found
    device = await session.get(Device, device_id)
    if device is None:
        return DenialReason.attestation
    return GateInputs(ticket=ticket, event=event, venue=venue, device=device)


def evaluate_gate(
    inputs: GateInputs,
    *,
    auth_session: Session,
    latitude: float,
    longitude: float,
    now: datetime,
) -> DenialReason | None:
    """Return the first failing gate, or None when every gate passes."""
    if inputs.ticket.state not in {TicketState.issued, TicketState.entry_pending}:
        return DenialReason.state
    last_asserted = auth_session.last_asserted_at
    if last_asserted is None:
        return DenialReason.reassertion
    if last_asserted.tzinfo is None:
        last_asserted = last_asserted.replace(tzinfo=UTC)
    if now - last_asserted > timedelta(
        seconds=settings.ticket_qr_reassert_window_seconds
    ):
        return DenialReason.reassertion
    if inputs.device.revoked_at is not None:
        return DenialReason.attestation
    if inputs.device.attested_at is None:
        return DenialReason.attestation
    attested = inputs.device.attested_at
    if attested.tzinfo is None:
        attested = attested.replace(tzinfo=UTC)
    if now - attested > timedelta(hours=settings.ticket_qr_attestation_max_age_hours):
        return DenialReason.attestation
    distance = haversine_metres(
        lat1=latitude,
        lon1=longitude,
        lat2=float(inputs.venue.latitude),
        lon2=float(inputs.venue.longitude),
    )
    if distance > inputs.venue.geofence_radius_m:
        return DenialReason.geofence
    return None


# keep the queries importable for the integration tests
__all__ = [
    "DenialReason",
    "GateInputs",
    "evaluate_gate",
    "haversine_metres",
    "load_inputs",
    "select",
]
