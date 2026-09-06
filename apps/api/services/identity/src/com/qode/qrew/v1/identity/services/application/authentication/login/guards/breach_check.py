# checks a login password against known breaches and records the outcome
import uuid

import structlog

from com.qode.qrew.v1.identity.services.application.authentication.token.security import (
    is_password_pwned,
)
from com.qode.qrew.v1.identity.models.audit import AuditAction
from com.qode.qrew.v1.identity.services.application.audit import AuditService

logger = structlog.get_logger(__name__)


class PasswordBreachChecker:
    # stores the audit service the checker uses
    def __init__(self, audit: AuditService) -> None:
        self._audit = audit

    # checks a password against have i been pwned and records a match
    async def is_compromised(
        self,
        user_id: uuid.UUID,
        password: str,
        ip_address: str | None,
    ) -> bool:
        try:
            compromised = await is_password_pwned(password)
        except Exception as exc:
            await logger.awarning("hibp_check_error", user_id=str(user_id), error=repr(exc))
            return False
        if not compromised:
            return False
        await logger.awarning("login_compromised_password", user_id=str(user_id))
        await self._audit_safe(user_id, ip_address)
        return True

    # records the compromised password without letting a failure interrupt the login
    async def _audit_safe(self, user_id: uuid.UUID, ip_address: str | None) -> None:
        try:
            await self._audit.record(
                action=AuditAction.LOGIN_COMPROMISED_PASSWORD,
                actor_id=user_id,
                entity_type="user",
                entity_id=str(user_id),
                ip_address=ip_address,
            )
        except Exception as exc:
            await logger.awarning(
                "audit_write_failed", action=AuditAction.LOGIN_COMPROMISED_PASSWORD, error=repr(exc)
            )
