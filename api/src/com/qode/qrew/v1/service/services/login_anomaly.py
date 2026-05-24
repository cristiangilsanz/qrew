from datetime import UTC, datetime, timedelta

import redis.asyncio as aioredis
import structlog

from com.qode.qrew.v1.service.models.audit import AuditAction, AuditEvent
from com.qode.qrew.v1.service.models.user import User
from com.qode.qrew.v1.service.repositories.session import SessionRepository
from com.qode.qrew.v1.service.services.audit import AuditService
from com.qode.qrew.v1.service.services.geoip import GeoIpService
from com.qode.qrew.v1.service.services.notification import NotificationDispatcher
from com.qode.qrew.v1.service.settings import settings

_BLACKLIST_JTI_PREFIX = "blacklist:jti:"

logger = structlog.get_logger(__name__)


class LoginAnomalyService:
    def __init__(
        self,
        geoip: GeoIpService,
        audit: AuditService,
        session_repo: SessionRepository,
        notifier: NotificationDispatcher,
        redis: aioredis.Redis,  # type: ignore[type-arg]
    ) -> None:
        self._geoip = geoip
        self._audit = audit
        self._session_repo = session_repo
        self._notifier = notifier
        self._redis = redis

    async def check(
        self,
        user: User,
        ip_address: str | None,
        device_fingerprint: str | None,
    ) -> None:
        """Run all anomaly checks. Never raises — anomalies are handled internally."""
        reasons: list[str] = []

        if ip_address:
            travel = await self._check_impossible_travel(user, ip_address)
            if travel:
                reasons.append(travel)

        if device_fingerprint:
            concurrent = await self._check_concurrent_device(user, device_fingerprint)
            if concurrent:
                reasons.append(concurrent)

        if not reasons:
            return

        reason_str = "; ".join(reasons)
        await logger.awarning(
            "login_anomaly_detected", user_id=str(user.id), reason=reason_str
        )

        try:
            await self._audit.record(
                action=AuditAction.LOGIN_ANOMALY_DETECTED,
                actor_id=user.id,
                entity_type="user",
                entity_id=str(user.id),
                ip_address=ip_address,
                device_fingerprint_hash=device_fingerprint,
                payload={"reason": reason_str},
            )
        except Exception:
            await logger.awarning(
                "audit_write_failed", action=AuditAction.LOGIN_ANOMALY_DETECTED
            )

        if settings.anomaly_kill_sessions_on_detection:
            try:
                jtis = await self._session_repo.delete_all_by_user_id(user.id)
                ttl = int(
                    timedelta(days=settings.refresh_token_expire_days).total_seconds()
                )
                for jti in jtis:
                    await self._redis.setex(_BLACKLIST_JTI_PREFIX + jti, ttl, "1")
                await logger.awarning("anomaly_sessions_killed", user_id=str(user.id))
            except Exception:
                await logger.awarning(
                    "anomaly_session_kill_failed", user_id=str(user.id)
                )

        try:
            await self._notifier.send_login_anomaly_alert(
                user.email, user.full_name, reason_str, ip_address
            )
        except Exception:
            await logger.awarning("notification_failed", action="login_anomaly_alert")

    async def _check_impossible_travel(self, user: User, current_ip: str) -> str | None:
        current_loc = self._geoip.locate(current_ip)
        if current_loc is None:
            return None
        try:
            events = await self._audit.get_recent_login_events(user.id, limit=5)
        except Exception:
            return None
        prev_events = [
            e
            for e in events
            if e.payload.get("setup_complete") is True and e.ip_address
        ]
        if not prev_events:
            return None
        return self._travel_anomaly_reason(current_loc, prev_events[0])

    def _travel_anomaly_reason(
        self,
        current_loc: tuple[float, float],
        prev_event: AuditEvent,
    ) -> str | None:
        prev_ip = prev_event.ip_address
        if not prev_ip:
            return None
        prev_loc = self._geoip.locate(prev_ip)
        if prev_loc is None:
            return None
        distance_km = self._geoip.distance_km(prev_loc, current_loc)
        now = datetime.now(UTC)
        prev_time = prev_event.created_at
        if prev_time.tzinfo is None:
            prev_time = prev_time.replace(tzinfo=UTC)
        elapsed_s = (now - prev_time).total_seconds()
        if elapsed_s <= 0:
            return None
        speed_kmh = (distance_km / elapsed_s) * 3600
        if speed_kmh > settings.anomaly_impossible_travel_kmh:
            return (
                f"impossible_travel: {distance_km:.0f} km "
                f"in {elapsed_s:.0f}s ({speed_kmh:.0f} km/h)"
            )
        return None

    async def _check_concurrent_device(
        self, user: User, current_fingerprint: str
    ) -> str | None:
        try:
            sessions = await self._session_repo.get_all_by_user_id(user.id)
        except Exception:
            return None

        window = timedelta(minutes=settings.anomaly_concurrent_window_minutes)
        now = datetime.now(UTC)

        for session in sessions:
            if not session.device_fingerprint:
                continue
            if session.device_fingerprint == current_fingerprint:
                continue
            last_used = session.last_used_at
            if last_used.tzinfo is None:
                last_used = last_used.replace(tzinfo=UTC)
            if (now - last_used) <= window:
                return "concurrent_device: active session from a different device"

        return None
