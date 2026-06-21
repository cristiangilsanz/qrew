import uuid

import structlog

from com.qode.qrew.v1.identity.models.audit import AuditAction
from com.qode.qrew.v1.identity.models.user import User
from com.qode.qrew.v1.identity.models.fingerprint import DeviceFingerprint
from com.qode.qrew.v1.identity.repositories.fingerprint import (
    DeviceFingerprintRepository,
)
from com.qode.qrew.v1.identity.services.application.audit import AuditService
from com.qode.qrew.v1.identity.core.config import settings

logger = structlog.get_logger(__name__)

_HEADLESS_SIGNALS = [
    "HeadlessChrome",
    "PhantomJS",
    "Selenium",
    "WebDriver",
    "puppeteer",
    "playwright",
    "Headless",
]


def _is_headless(user_agent: str | None) -> bool:
    if not user_agent:
        return False
    lower = user_agent.lower()
    return any(sig.lower() in lower for sig in _HEADLESS_SIGNALS)


class FingerprintService:
    def __init__(
        self,
        repo: DeviceFingerprintRepository,
        audit: AuditService,
    ) -> None:
        self._repo = repo
        self._audit = audit

    async def report(
        self,
        user: User,
        fingerprint_hash: str,
        user_agent: str | None,
        ip_address: str | None,
    ) -> bool:
        """Records a device fingerprint and flags suspicious activity patterns."""
        record = DeviceFingerprint(
            id=uuid.uuid4(),
            user_id=user.id,
            fingerprint_hash=fingerprint_hash,
            user_agent=user_agent,
            ip_address=ip_address,
            account_count_at_seen=1,
        )

        account_count = await self._repo.upsert(record)

        flagged = False

        headless = _is_headless(user_agent)
        if headless:
            flagged = True
            await logger.awarning(
                "fingerprint_headless_detected",
                user_id=str(user.id),
                fingerprint_hash=fingerprint_hash,
            )
            try:
                await self._audit.record(
                    action=AuditAction.FINGERPRINT_HEADLESS_FLAG,
                    actor_id=user.id,
                    entity_type="user",
                    entity_id=str(user.id),
                    payload={
                        "fingerprint_hash": fingerprint_hash,
                        "user_agent": user_agent,
                    },
                )
            except Exception as exc:
                await logger.awarning(
                    "audit_write_failed",
                    action=AuditAction.FINGERPRINT_HEADLESS_FLAG,
                    error=repr(exc),
                )

        if account_count > settings.fingerprint_multi_account_threshold:
            flagged = True
            await logger.awarning(
                "fingerprint_multi_account_detected",
                user_id=str(user.id),
                fingerprint_hash=fingerprint_hash,
                account_count=account_count,
            )
            try:
                await self._audit.record(
                    action=AuditAction.FINGERPRINT_MULTI_ACCOUNT_FLAG,
                    actor_id=user.id,
                    entity_type="user",
                    entity_id=str(user.id),
                    payload={
                        "fingerprint_hash": fingerprint_hash,
                        "account_count": account_count,
                    },
                )
            except Exception as exc:
                await logger.awarning(
                    "audit_write_failed",
                    action=AuditAction.FINGERPRINT_MULTI_ACCOUNT_FLAG,
                    error=repr(exc),
                )

        await self._publish_fingerprint_seen(fingerprint_hash)

        await logger.ainfo(
            "fingerprint_reported",
            user_id=str(user.id),
            account_count=account_count,
            flagged=flagged,
        )
        return flagged

    async def _publish_fingerprint_seen(self, fingerprint_hash: str) -> None:
        try:
            from datetime import UTC, datetime

            from messaging.publisher import publish as nats_publish  # type: ignore[import-not-found]
            from contracts.messaging.envelope import EventEnvelope  # type: ignore[import-not-found]

            now = datetime.now(UTC)
            envelope = EventEnvelope(
                occurred_at=now,
                aggregate_type="fingerprint",
                aggregate_id=fingerprint_hash,
                actor_id="system",
                data={
                    "fingerprint_hash": fingerprint_hash,
                    "occurred_at": now.isoformat(),
                },
            )
            await nats_publish("identity.fingerprint.seen.v1", envelope)
        except Exception as exc:
            await logger.awarning(
                "nats_publish_failed",
                subject="identity.fingerprint.seen.v1",
                error=repr(exc),
            )

    async def get_by_hash(self, fingerprint_hash: str) -> list[uuid.UUID]:
        """Returns all user identifiers associated with a given device fingerprint."""
        return await self._repo.get_user_ids_by_hash(fingerprint_hash)
