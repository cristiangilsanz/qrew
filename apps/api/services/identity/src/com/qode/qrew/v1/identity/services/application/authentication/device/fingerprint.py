# records device fingerprints and flags headless or multi account abuse
import uuid

import structlog

from outbox import record as record_event

from com.qode.qrew.v1.identity.models.event_outbox import EventOutbox
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


# checks whether a user agent looks like an automation tool
def _is_headless(user_agent: str | None) -> bool:
    if not user_agent:
        return False
    lower = user_agent.lower()
    return any(sig.lower() in lower for sig in _HEADLESS_SIGNALS)


class FingerprintService:
    # stores the repository and audit service the service uses
    def __init__(
        self,
        repo: DeviceFingerprintRepository,
        audit: AuditService,
    ) -> None:
        self._repo = repo
        self._audit = audit

    # records a sighting and flags it if it looks headless or multi account
    async def report(
        self,
        user: User,
        fingerprint_hash: str,
        user_agent: str | None,
        ip_address: str | None,
    ) -> bool:
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

    # publishes that a fingerprint was seen onto the shared nats connection
    async def _publish_fingerprint_seen(self, fingerprint_hash: str) -> None:
        await record_event(
            self._repo.session,
            EventOutbox,
            subject="identity.fingerprint.seen.v1",
            aggregate_type="fingerprint",
            aggregate_id=fingerprint_hash,
            data={"fingerprint_hash": fingerprint_hash},
        )

    # lists the accounts a fingerprint has been seen on
    async def get_by_hash(self, fingerprint_hash: str) -> list[uuid.UUID]:
        return await self._repo.get_user_ids_by_hash(fingerprint_hash)
