import uuid

import structlog

from com.qode.qrew.v1.service.models.audit.audit import AuditAction
from com.qode.qrew.v1.service.models.auth.user import User
from com.qode.qrew.v1.service.models.device.fingerprint import DeviceFingerprint
from com.qode.qrew.v1.service.repositories.device.fingerprint import (
    DeviceFingerprintRepository,
)
from com.qode.qrew.v1.service.services.audit import AuditService
from com.qode.qrew.v1.service.settings import settings

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
        """Upsert fingerprint record; flag if multi-account or headless."""
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
            except Exception:
                await logger.awarning(
                    "audit_write_failed",
                    action=AuditAction.FINGERPRINT_HEADLESS_FLAG,
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
            except Exception:
                await logger.awarning(
                    "audit_write_failed",
                    action=AuditAction.FINGERPRINT_MULTI_ACCOUNT_FLAG,
                )

        await logger.ainfo(
            "fingerprint_reported",
            user_id=str(user.id),
            account_count=account_count,
            flagged=flagged,
        )
        return flagged

    async def get_by_hash(self, fingerprint_hash: str) -> list[uuid.UUID]:
        """Return all distinct user_ids linked to the given hash."""
        return await self._repo.get_user_ids_by_hash(fingerprint_hash)
