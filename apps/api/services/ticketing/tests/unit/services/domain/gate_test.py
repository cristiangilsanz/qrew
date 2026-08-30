# tests the rules that decide whether a ticket may show its qr at the gate
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import patch

from com.qode.qrew.v1.ticketing.models.ticket import TicketState
from com.qode.qrew.v1.ticketing.services.domain.gate import (
    DenialReason,
    GateInputs,
    evaluate_gate,
    haversine_metres,
)

NOW = datetime(2026, 6, 1, 20, 0, tzinfo=UTC)

_PATCH_SETTINGS = "com.qode.qrew.v1.ticketing.services.domain.gate.settings"


# builds settings that leave attestation and geofence switched on
def _settings(*, skip_attestation: bool = False, skip_geofence: bool = False) -> SimpleNamespace:
    return SimpleNamespace(
        ticket_qr_skip_attestation=skip_attestation,
        ticket_qr_skip_geofence=skip_geofence,
        ticket_qr_reassert_window_seconds=300,
        ticket_qr_attestation_max_age_hours=24,
    )


# builds the gate inputs for a ticket that should be allowed through
def _inputs(
    *,
    state: TicketState = TicketState.issued,
    revoked_at: datetime | None = None,
    attested_at: datetime | None = NOW,
    latitude: float = 40.0,
    longitude: float = -3.0,
    radius: int = 500,
    starts_at: datetime | None = NOW - timedelta(hours=1),
    ends_at: datetime | None = NOW + timedelta(hours=3),
) -> GateInputs:
    return GateInputs(
        ticket=SimpleNamespace(state=state),  # type: ignore[arg-type]
        event_ctx=SimpleNamespace(  # type: ignore[arg-type]
            latitude=latitude,
            longitude=longitude,
            geofence_radius_m=radius,
            starts_at=starts_at,
            ends_at=ends_at,
        ),
        device_ctx=SimpleNamespace(revoked_at=revoked_at, attested_at=attested_at),  # type: ignore[arg-type]
    )


class TestHaversine:
    # verifies that the same point is zero metres away
    def test_reports_no_distance_between_a_point_and_itself(self) -> None:
        assert haversine_metres(lat1=40.0, lon1=-3.0, lat2=40.0, lon2=-3.0) == 0

    # verifies that a known separation lands in the expected range
    def test_reports_a_plausible_distance(self) -> None:
        metres = haversine_metres(lat1=40.0, lon1=-3.0, lat2=40.01, lon2=-3.0)
        assert 1000 < metres < 1200


class TestEvaluateGate:
    # verifies that a ticket in the wrong state is refused before anything else
    def test_denies_a_ticket_in_the_wrong_state(self) -> None:
        with patch(_PATCH_SETTINGS, _settings()):
            reason = evaluate_gate(
                _inputs(state=TicketState.redeemed),
                last_asserted_at=NOW,
                latitude=40.0,
                longitude=-3.0,
                now=NOW,
            )
        assert reason is DenialReason.state

    # verifies that a device that never asserted recently is refused
    def test_denies_a_stale_reassertion(self) -> None:
        with patch(_PATCH_SETTINGS, _settings()):
            reason = evaluate_gate(
                _inputs(),
                last_asserted_at=NOW - timedelta(hours=1),
                latitude=40.0,
                longitude=-3.0,
                now=NOW,
            )
        assert reason is DenialReason.reassertion

    # verifies that a revoked device is refused
    def test_denies_a_revoked_device(self) -> None:
        with patch(_PATCH_SETTINGS, _settings()):
            reason = evaluate_gate(
                _inputs(revoked_at=NOW),
                last_asserted_at=NOW,
                latitude=40.0,
                longitude=-3.0,
                now=NOW,
            )
        assert reason is DenialReason.attestation

    # verifies that an attestation older than its window is refused
    def test_denies_an_old_attestation(self) -> None:
        with patch(_PATCH_SETTINGS, _settings()):
            reason = evaluate_gate(
                _inputs(attested_at=NOW - timedelta(days=3)),
                last_asserted_at=NOW,
                latitude=40.0,
                longitude=-3.0,
                now=NOW,
            )
        assert reason is DenialReason.attestation

    # verifies that standing outside the venue radius is refused
    def test_denies_a_position_outside_the_fence(self) -> None:
        with patch(_PATCH_SETTINGS, _settings(skip_attestation=True)):
            reason = evaluate_gate(
                _inputs(),
                last_asserted_at=NOW,
                latitude=41.0,
                longitude=-3.0,
                now=NOW,
            )
        assert reason is DenialReason.geofence

    # verifies that a venue without coordinates cannot be fenced
    def test_denies_when_the_venue_has_no_coordinates(self) -> None:
        with patch(_PATCH_SETTINGS, _settings(skip_attestation=True)):
            reason = evaluate_gate(
                _inputs(latitude=None, longitude=None, radius=None),  # type: ignore[arg-type]
                last_asserted_at=NOW,
                latitude=40.0,
                longitude=-3.0,
                now=NOW,
            )
        assert reason is DenialReason.geofence

    # verifies that showing a qr long before the doors open is refused
    def test_denies_outside_the_time_window(self) -> None:
        with patch(_PATCH_SETTINGS, _settings(skip_attestation=True, skip_geofence=True)):
            reason = evaluate_gate(
                _inputs(starts_at=NOW + timedelta(days=2), ends_at=NOW + timedelta(days=3)),
                last_asserted_at=NOW,
                latitude=40.0,
                longitude=-3.0,
                now=NOW,
            )
        assert reason is DenialReason.time_window

    # verifies that a ticket meeting every rule is allowed through
    def test_allows_a_ticket_that_meets_every_rule(self) -> None:
        with patch(_PATCH_SETTINGS, _settings()):
            reason = evaluate_gate(
                _inputs(),
                last_asserted_at=NOW,
                latitude=40.0,
                longitude=-3.0,
                now=NOW,
            )
        assert reason is None

    # verifies that a ticket already scanning may still show its qr again
    def test_allows_a_ticket_that_is_already_scanning(self) -> None:
        with patch(_PATCH_SETTINGS, _settings()):
            reason = evaluate_gate(
                _inputs(state=TicketState.scanning),
                last_asserted_at=NOW,
                latitude=40.0,
                longitude=-3.0,
                now=NOW,
            )
        assert reason is None
