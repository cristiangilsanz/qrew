"""Unit tests for LoginAnomalyService and GeoIpService."""

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from com.qode.qrew.v1.service.models.audit.audit import AuditAction, AuditEvent
from com.qode.qrew.v1.service.services.auth.login_anomaly import LoginAnomalyService
from com.qode.qrew.v1.service.services.infra.geoip import GeoIpService, haversine_km

_GEOIP_MODULE = "com.qode.qrew.v1.service.services.infra.geoip.geoip2.database.Reader"


def _make_user() -> MagicMock:
    user = MagicMock()
    user.id = uuid.uuid4()
    user.email = "user@example.com"
    user.full_name = "Test User"
    return user


def _make_login_event(
    ip_address: str = "1.2.3.4",
    setup_complete: bool = True,
    minutes_ago: int = 60,
) -> AuditEvent:
    event = MagicMock(spec=AuditEvent)
    event.ip_address = ip_address
    event.payload = {"setup_complete": setup_complete}
    event.created_at = datetime.now(UTC) - timedelta(minutes=minutes_ago)
    return event


def _make_anomaly_service(
    geoip: GeoIpService | None = None,
    audit: AsyncMock | None = None,
    session_repo: AsyncMock | None = None,
    notifier: AsyncMock | None = None,
    redis: AsyncMock | None = None,
) -> LoginAnomalyService:
    return LoginAnomalyService(
        geoip=geoip or MagicMock(spec=GeoIpService),
        audit=audit or AsyncMock(),
        session_repo=session_repo or AsyncMock(),
        notifier=notifier or AsyncMock(),
        redis=redis or AsyncMock(),
    )


def test_haversine_same_point_is_zero() -> None:
    assert haversine_km(40.0, -3.0, 40.0, -3.0) == pytest.approx(0.0)  # type: ignore[reportUnknownMemberType]


def test_haversine_madrid_to_barcelona_roughly_500km() -> None:
    dist = haversine_km(40.4, -3.7, 41.4, 2.2)
    assert 490 < dist < 520


def test_haversine_madrid_to_new_york_roughly_5700km() -> None:
    dist = haversine_km(40.4, -3.7, 40.7, -74.0)
    assert 5600 < dist < 5900


def test_geoip_returns_none_when_db_missing() -> None:
    svc = GeoIpService("/nonexistent/path.mmdb")
    assert svc.locate("1.2.3.4") is None


def test_geoip_returns_none_for_reader_exception() -> None:
    mock_reader = MagicMock()
    mock_reader.city.side_effect = Exception("no data")
    with patch(_GEOIP_MODULE, return_value=mock_reader):
        svc = GeoIpService("/fake/path.mmdb")
    assert svc.locate("1.2.3.4") is None


def test_geoip_returns_none_when_lat_lon_missing() -> None:
    mock_reader = MagicMock()
    mock_reader.city.return_value.location.latitude = None
    mock_reader.city.return_value.location.longitude = None
    with patch(_GEOIP_MODULE, return_value=mock_reader):
        svc = GeoIpService("/fake/path.mmdb")
    assert svc.locate("1.2.3.4") is None


def test_geoip_returns_coordinates_when_reader_succeeds() -> None:
    mock_reader = MagicMock()
    mock_reader.city.return_value.location.latitude = 40.4
    mock_reader.city.return_value.location.longitude = -3.7
    with patch(_GEOIP_MODULE, return_value=mock_reader):
        svc = GeoIpService("/fake/path.mmdb")
    result = svc.locate("1.2.3.4")
    assert result == pytest.approx((40.4, -3.7))  # type: ignore[reportUnknownMemberType]


async def test_check_does_nothing_when_no_anomaly() -> None:
    geoip = MagicMock(spec=GeoIpService)
    geoip.locate.return_value = (40.4, -3.7)
    geoip.distance_km.return_value = 5.0

    audit = AsyncMock()
    audit.get_recent_login_events = AsyncMock(
        return_value=[_make_login_event(minutes_ago=120)]
    )

    svc = _make_anomaly_service(geoip=geoip, audit=audit)
    await svc.check(_make_user(), "1.2.3.4", "fp-abc")

    audit.record.assert_not_awaited()


async def test_check_skips_impossible_travel_when_no_ip() -> None:
    audit = AsyncMock()
    svc = _make_anomaly_service(audit=audit)
    await svc.check(_make_user(), ip_address=None, device_fingerprint=None)
    audit.record.assert_not_awaited()


async def test_check_skips_travel_when_geoip_returns_none() -> None:
    geoip = MagicMock(spec=GeoIpService)
    geoip.locate.return_value = None

    audit = AsyncMock()
    svc = _make_anomaly_service(geoip=geoip, audit=audit)
    await svc.check(_make_user(), "1.2.3.4", None)

    audit.record.assert_not_awaited()


async def test_check_detects_impossible_travel() -> None:
    geoip = MagicMock(spec=GeoIpService)
    geoip.locate.return_value = (40.4, -3.7)
    geoip.distance_km.return_value = 8000.0

    audit = AsyncMock()
    audit.get_recent_login_events = AsyncMock(
        return_value=[_make_login_event(minutes_ago=10)]
    )
    notifier = AsyncMock()
    svc = _make_anomaly_service(geoip=geoip, audit=audit, notifier=notifier)

    with patch(
        "com.qode.qrew.v1.service.services.auth.login_anomaly.settings"
    ) as mock_settings:
        mock_settings.anomaly_impossible_travel_kmh = 1000.0
        mock_settings.anomaly_kill_sessions_on_detection = False
        mock_settings.refresh_token_expire_days = 7
        mock_settings.anomaly_concurrent_window_minutes = 5
        await svc.check(_make_user(), "5.6.7.8", None)

    audit.record.assert_awaited_once()
    call_kwargs = audit.record.call_args.kwargs
    assert call_kwargs["action"] == AuditAction.LOGIN_ANOMALY_DETECTED
    assert "impossible_travel" in call_kwargs["payload"]["reason"]
    notifier.send_login_anomaly_alert.assert_awaited_once()


async def test_check_does_not_flag_slow_travel() -> None:
    geoip = MagicMock(spec=GeoIpService)
    geoip.locate.return_value = (40.4, -3.7)
    geoip.distance_km.return_value = 50.0

    audit = AsyncMock()
    audit.get_recent_login_events = AsyncMock(
        return_value=[_make_login_event(minutes_ago=120)]
    )
    svc = _make_anomaly_service(geoip=geoip, audit=audit)

    with patch(
        "com.qode.qrew.v1.service.services.auth.login_anomaly.settings"
    ) as mock_settings:
        mock_settings.anomaly_impossible_travel_kmh = 1000.0
        mock_settings.anomaly_kill_sessions_on_detection = False
        mock_settings.anomaly_concurrent_window_minutes = 5
        await svc.check(_make_user(), "1.2.3.4", None)

    audit.record.assert_not_awaited()


async def test_check_detects_concurrent_device() -> None:
    other_session = MagicMock()
    other_session.device_fingerprint = "fp-other"
    other_session.last_used_at = datetime.now(UTC) - timedelta(minutes=2)

    session_repo = AsyncMock()
    session_repo.get_all_by_user_id = AsyncMock(return_value=[other_session])

    audit = AsyncMock()
    notifier = AsyncMock()
    geoip = MagicMock(spec=GeoIpService)
    geoip.locate.return_value = None

    svc = _make_anomaly_service(
        geoip=geoip, audit=audit, session_repo=session_repo, notifier=notifier
    )

    with patch(
        "com.qode.qrew.v1.service.services.auth.login_anomaly.settings"
    ) as mock_settings:
        mock_settings.anomaly_impossible_travel_kmh = 1000.0
        mock_settings.anomaly_kill_sessions_on_detection = False
        mock_settings.refresh_token_expire_days = 7
        mock_settings.anomaly_concurrent_window_minutes = 5
        await svc.check(_make_user(), None, "fp-current")

    audit.record.assert_awaited_once()
    call_kwargs = audit.record.call_args.kwargs
    assert call_kwargs["action"] == AuditAction.LOGIN_ANOMALY_DETECTED
    assert "concurrent_device" in call_kwargs["payload"]["reason"]
    notifier.send_login_anomaly_alert.assert_awaited_once()


async def test_check_ignores_session_with_same_fingerprint() -> None:
    same_session = MagicMock()
    same_session.device_fingerprint = "fp-same"
    same_session.last_used_at = datetime.now(UTC) - timedelta(minutes=1)

    session_repo = AsyncMock()
    session_repo.get_all_by_user_id = AsyncMock(return_value=[same_session])

    audit = AsyncMock()
    geoip = MagicMock(spec=GeoIpService)
    geoip.locate.return_value = None

    svc = _make_anomaly_service(geoip=geoip, audit=audit, session_repo=session_repo)

    with patch(
        "com.qode.qrew.v1.service.services.auth.login_anomaly.settings"
    ) as mock_settings:
        mock_settings.anomaly_impossible_travel_kmh = 1000.0
        mock_settings.anomaly_kill_sessions_on_detection = False
        mock_settings.anomaly_concurrent_window_minutes = 5
        await svc.check(_make_user(), None, "fp-same")

    audit.record.assert_not_awaited()


async def test_check_ignores_old_sessions_outside_window() -> None:
    old_session = MagicMock()
    old_session.device_fingerprint = "fp-old"
    old_session.last_used_at = datetime.now(UTC) - timedelta(minutes=30)

    session_repo = AsyncMock()
    session_repo.get_all_by_user_id = AsyncMock(return_value=[old_session])

    audit = AsyncMock()
    geoip = MagicMock(spec=GeoIpService)
    geoip.locate.return_value = None

    svc = _make_anomaly_service(geoip=geoip, audit=audit, session_repo=session_repo)

    with patch(
        "com.qode.qrew.v1.service.services.auth.login_anomaly.settings"
    ) as mock_settings:
        mock_settings.anomaly_impossible_travel_kmh = 1000.0
        mock_settings.anomaly_kill_sessions_on_detection = False
        mock_settings.anomaly_concurrent_window_minutes = 5
        await svc.check(_make_user(), None, "fp-current")

    audit.record.assert_not_awaited()


async def test_kill_sessions_when_configured() -> None:
    geoip = MagicMock(spec=GeoIpService)
    geoip.locate.return_value = (40.4, -3.7)
    geoip.distance_km.return_value = 9000.0

    audit = AsyncMock()
    audit.get_recent_login_events = AsyncMock(
        return_value=[_make_login_event(minutes_ago=5)]
    )

    session_repo = AsyncMock()
    session_repo.delete_all_by_user_id = AsyncMock(return_value=["jti-1", "jti-2"])
    redis = AsyncMock()
    notifier = AsyncMock()

    svc = _make_anomaly_service(
        geoip=geoip,
        audit=audit,
        session_repo=session_repo,
        redis=redis,
        notifier=notifier,
    )

    with patch(
        "com.qode.qrew.v1.service.services.auth.login_anomaly.settings"
    ) as mock_settings:
        mock_settings.anomaly_impossible_travel_kmh = 1000.0
        mock_settings.anomaly_kill_sessions_on_detection = True
        mock_settings.refresh_token_expire_days = 7
        mock_settings.anomaly_concurrent_window_minutes = 5
        await svc.check(_make_user(), "9.9.9.9", None)

    session_repo.delete_all_by_user_id.assert_awaited_once()
    assert redis.setex.await_count == 2
