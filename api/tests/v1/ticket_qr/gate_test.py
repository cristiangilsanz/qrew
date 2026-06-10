import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

import jwt

from com.qode.qrew.v1.service.core.auth import jwt_keys
from com.qode.qrew.v1.service.models.auth.session import Session
from com.qode.qrew.v1.service.models.device.device import Device
from com.qode.qrew.v1.service.models.event import Event, EventStatus
from com.qode.qrew.v1.service.models.ticket import Ticket, TicketState
from com.qode.qrew.v1.service.models.venue import Venue
from com.qode.qrew.v1.service.services.audit import AuditService
from com.qode.qrew.v1.service.services.ticket_qr import (
    DenialReason,
    GateInputs,
    evaluate_gate,
    haversine_metres,
    mint_qr,
)
from com.qode.qrew.v1.service.settings import settings

WEMBLEY_LAT = 51.555973
WEMBLEY_LON = -0.279672


def _now() -> datetime:
    return datetime(2026, 7, 1, 19, 0, tzinfo=UTC)


def _ticket(state: TicketState = TicketState.issued) -> Ticket:
    return Ticket(
        id=uuid.uuid4(),
        reservation_id=uuid.uuid4(),
        event_id=uuid.uuid4(),
        ticket_type_id=uuid.uuid4(),
        owner_user_id=uuid.uuid4(),
        state=state,
    )


def _event(ticket: Ticket) -> Event:
    return Event(
        id=ticket.event_id,
        organisation_id=uuid.uuid4(),
        venue_id=uuid.uuid4(),
        name="Concert",
        description=None,
        starts_at=_now(),
        ends_at=_now() + timedelta(hours=3),
        sale_starts_at=_now() - timedelta(days=10),
        sale_ends_at=_now() - timedelta(hours=1),
        max_tickets_per_user=4,
        status=EventStatus.published,
        organiser_name="Live",
        venue_city="London",
    )


def _venue(event: Event, radius: int = 200) -> Venue:
    return Venue(
        id=event.venue_id,
        name="Wembley",
        address_line="Olympic Way",
        city="London",
        country="GB",
        latitude=Decimal(str(WEMBLEY_LAT)),
        longitude=Decimal(str(WEMBLEY_LON)),
        geofence_radius_m=radius,
        timezone="Europe/London",
        description=None,
    )


def _device(*, attested_minutes_ago: int = 30, revoked: bool = False) -> Device:
    now = _now()
    return Device(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        name="Phone",
        public_key=b"\x01" * 65,
        attested_at=now - timedelta(minutes=attested_minutes_ago),
        revoked_at=(now if revoked else None),
    )


def _session(*, asserted_seconds_ago: int = 10) -> Session:
    return Session(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        jti=uuid.uuid4().hex,
        device_id=uuid.uuid4(),
        last_asserted_at=_now() - timedelta(seconds=asserted_seconds_ago),
    )


def _inputs(
    *,
    state: TicketState = TicketState.issued,
    radius: int = 200,
    device: Device | None = None,
) -> GateInputs:
    ticket = _ticket(state=state)
    event = _event(ticket)
    venue = _venue(event, radius=radius)
    return GateInputs(
        ticket=ticket,
        event=event,
        venue=venue,
        device=device or _device(),
    )


def test_haversine_matches_known_distance() -> None:
    # Wembley to Wembley Park station ~ 700m
    d = haversine_metres(
        lat1=WEMBLEY_LAT,
        lon1=WEMBLEY_LON,
        lat2=51.5635,
        lon2=-0.2795,
    )
    assert 600 < d < 900


def test_gate_passes_when_all_conditions_satisfied() -> None:
    inputs = _inputs()
    result = evaluate_gate(
        inputs,
        auth_session=_session(),
        latitude=WEMBLEY_LAT,
        longitude=WEMBLEY_LON,
        now=_now(),
    )
    assert result is None


def test_gate_rejects_unissued_ticket() -> None:
    inputs = _inputs(state=TicketState.reserved)
    result = evaluate_gate(
        inputs,
        auth_session=_session(),
        latitude=WEMBLEY_LAT,
        longitude=WEMBLEY_LON,
        now=_now(),
    )
    assert result == DenialReason.state


def test_gate_rejects_stale_reassertion() -> None:
    inputs = _inputs()
    stale_session = _session(asserted_seconds_ago=600)
    result = evaluate_gate(
        inputs,
        auth_session=stale_session,
        latitude=WEMBLEY_LAT,
        longitude=WEMBLEY_LON,
        now=_now(),
    )
    assert result == DenialReason.reassertion


def test_gate_rejects_revoked_device() -> None:
    inputs = _inputs(device=_device(revoked=True))
    result = evaluate_gate(
        inputs,
        auth_session=_session(),
        latitude=WEMBLEY_LAT,
        longitude=WEMBLEY_LON,
        now=_now(),
    )
    assert result == DenialReason.attestation


def test_gate_rejects_stale_attestation() -> None:
    inputs = _inputs(device=_device(attested_minutes_ago=48 * 60))
    result = evaluate_gate(
        inputs,
        auth_session=_session(),
        latitude=WEMBLEY_LAT,
        longitude=WEMBLEY_LON,
        now=_now(),
    )
    assert result == DenialReason.attestation


def test_gate_rejects_outside_geofence() -> None:
    inputs = _inputs(radius=100)
    # Big Ben is ~13 km from Wembley
    result = evaluate_gate(
        inputs,
        auth_session=_session(),
        latitude=51.5007,
        longitude=-0.1246,
        now=_now(),
    )
    assert result == DenialReason.geofence


async def test_mint_includes_expected_claims() -> None:
    class _Audit(AuditService):
        recorded: list[Any] = []

        async def record(self, **kwargs: Any) -> None:  # type: ignore[override]
            self.recorded.append(kwargs)

    inputs = _inputs()
    user_id = inputs.ticket.owner_user_id
    settings.ticket_qr_mint_audit_sample_rate = 1
    minted = await mint_qr(
        inputs=inputs,
        user_id=user_id,
        device_id=inputs.device.id,
        audit=_Audit(),
        now=_now(),
    )
    payload = jwt.decode(
        minted.jwt,
        options={"verify_signature": False, "verify_aud": False},
    )
    assert payload["ticket_id"] == str(inputs.ticket.id)
    assert payload["event_id"] == str(inputs.event.id)
    assert payload["venue_id"] == str(inputs.venue.id)
    assert payload["device_id"] == str(inputs.device.id)
    assert payload["aud"] == settings.ticket_qr_audience
    assert payload["jti"] == minted.jti
    assert (
        minted.expires_at - minted.issued_at
    ).total_seconds() == settings.ticket_qr_ttl_seconds


async def test_jwt_signature_verifies_under_ticket_qr_purpose() -> None:
    class _Audit:
        async def record(self, **_kwargs: Any) -> None:
            return None

    inputs = _inputs()
    minted = await mint_qr(
        inputs=inputs,
        user_id=inputs.ticket.owner_user_id,
        device_id=inputs.device.id,
        audit=_Audit(),  # type: ignore[arg-type]
        now=datetime.now(UTC) - timedelta(seconds=1),
    )
    decoded = jwt.decode(
        minted.jwt,
        jwt_keys._KEYS[jwt_keys.TICKET_QR].public_pem,  # pyright: ignore[reportPrivateUsage]
        algorithms=["ES256"],
        options={"verify_aud": False},
    )
    assert decoded["sub"] == str(inputs.ticket.owner_user_id)
