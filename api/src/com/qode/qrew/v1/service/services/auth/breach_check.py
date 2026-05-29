import uuid

import structlog

from com.qode.qrew.v1.service.core.auth.security import is_password_pwned
from com.qode.qrew.v1.service.models.audit.audit import AuditAction
from com.qode.qrew.v1.service.services.audit import AuditService

logger = structlog.get_logger(__name__)


class PasswordBreachChecker:
    """Flag passwords that appear in known breach data."""

    def __init__(self, audit: AuditService) -> None:
        self._audit = audit

    async def is_compromised(
        self,
        user_id: uuid.UUID,
        password: str,
        ip_address: str | None,
    ) -> bool:
        """Check a password against known breach data and audit a hit."""
        try:
            compromised = await is_password_pwned(password)
        except Exception:
            await logger.awarning("hibp_check_error", user_id=str(user_id))
            return False
        if not compromised:
            return False
        await logger.awarning("login_compromised_password", user_id=str(user_id))
        await self._audit_safe(user_id, ip_address)
        return True

    async def _audit_safe(self, user_id: uuid.UUID, ip_address: str | None) -> None:
        """Record the compromised-password audit event without raising."""
        try:
            await self._audit.record(
                action=AuditAction.LOGIN_COMPROMISED_PASSWORD,
                actor_id=user_id,
                entity_type="user",
                entity_id=str(user_id),
                ip_address=ip_address,
            )
        except Exception:
            await logger.awarning(
                "audit_write_failed", action=AuditAction.LOGIN_COMPROMISED_PASSWORD
            )
