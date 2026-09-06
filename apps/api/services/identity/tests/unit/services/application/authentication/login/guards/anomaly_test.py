# tests the checks that flag a login as coming from somewhere unexpected
import uuid
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from com.qode.qrew.v1.identity.services.application.authentication.login.guards.anomaly import (
    LoginAnomalyService,
)

_MODULE = "com.qode.qrew.v1.identity.services.application.authentication.login.guards.anomaly"

MADRID = (40.4, -3.7)
SYDNEY = (-33.9, 151.2)


# builds an anomaly service whose collaborators are all stand ins
def _make_service(
    *,
    locations: dict[str, tuple[float, float]] | None = None,
    events: list[object] | None = None,
    distance_km: float = 0.0,
) -> tuple[LoginAnomalyService, MagicMock]:
    geoip = MagicMock()
    geoip.locate = MagicMock(side_effect=lambda ip: (locations or {}).get(ip))
    geoip.distance_km = MagicMock(return_value=distance_km)

    audit = MagicMock()
    audit.get_recent_login_events = AsyncMock(return_value=events or [])
    audit.record = AsyncMock()

    session_repo = MagicMock()
    session_repo.list_active_for_user = AsyncMock(return_value=[])

    notifier = MagicMock()
    notifier.send_login_anomaly_alert = AsyncMock()

    redis = MagicMock()
    redis.get = AsyncMock(return_value=None)
    redis.set = AsyncMock()

    service = LoginAnomalyService(geoip, audit, session_repo, notifier, redis)
    return service, notifier


# builds a stand in login entry from the audit trail
def _login_event(ip: str, *, minutes_ago: int) -> SimpleNamespace:
    return SimpleNamespace(
        ip_address=ip,
        created_at=datetime.now(UTC) - timedelta(minutes=minutes_ago),
        payload={"setup_complete": True},
    )


# builds a stand in user row
def _user() -> SimpleNamespace:
    return SimpleNamespace(id=uuid.uuid4(), email="user@example.com", full_name="Test User")


class TestImpossibleTravel:
    # verifies that an address the database cannot place raises nothing
    async def test_ignores_an_address_with_no_location(self) -> None:
        service, notifier = _make_service(locations={})
        await service.check(_user(), "10.0.0.1", None)  # type: ignore[arg-type]
        notifier.send_login_anomaly_alert.assert_not_awaited()

    # verifies that a first login has nothing to compare against
    async def test_ignores_a_login_with_no_history(self) -> None:
        service, notifier = _make_service(locations={"10.0.0.1": MADRID}, events=[])
        await service.check(_user(), "10.0.0.1", None)  # type: ignore[arg-type]
        notifier.send_login_anomaly_alert.assert_not_awaited()

    # verifies that a plausible journey is not flagged
    async def test_ignores_a_journey_that_is_possible(self) -> None:
        service, notifier = _make_service(
            locations={"10.0.0.1": MADRID, "10.0.0.2": MADRID},
            events=[_login_event("10.0.0.2", minutes_ago=600)],
            distance_km=20,
        )
        await service.check(_user(), "10.0.0.1", None)  # type: ignore[arg-type]
        notifier.send_login_anomaly_alert.assert_not_awaited()

    # verifies that a journey no traveller could make is reported
    async def test_reports_a_journey_that_is_impossible(self) -> None:
        service, notifier = _make_service(
            locations={"10.0.0.1": MADRID, "10.0.0.2": SYDNEY},
            events=[_login_event("10.0.0.2", minutes_ago=5)],
            distance_km=17_000,
        )
        fake_settings = SimpleNamespace(
            anomaly_impossible_travel_kmh=900,
            anomaly_kill_sessions_on_detection=False,
            refresh_token_expire_days=30,
        )
        with patch(f"{_MODULE}.settings", fake_settings):
            await service.check(_user(), "10.0.0.1", None)  # type: ignore[arg-type]
        notifier.send_login_anomaly_alert.assert_awaited_once()


class TestTravelReason:
    # verifies that an entry with no address cannot be compared
    def test_gives_no_reason_without_a_previous_address(self) -> None:
        service, _ = _make_service()
        event = SimpleNamespace(ip_address=None, created_at=datetime.now(UTC), payload={})
        assert service._travel_anomaly_reason(MADRID, event) is None  # type: ignore[arg-type]

    # verifies that an entry stamped in the future cannot imply a speed
    def test_gives_no_reason_when_no_time_has_passed(self) -> None:
        service, _ = _make_service(locations={"10.0.0.2": SYDNEY}, distance_km=17_000)
        event = SimpleNamespace(
            ip_address="10.0.0.2",
            created_at=datetime.now(UTC) + timedelta(minutes=5),
            payload={},
        )
        assert service._travel_anomaly_reason(MADRID, event) is None  # type: ignore[arg-type]
