import uuid

import structlog

from com.qode.qrew.v1.service.core.errors import DomainError
from com.qode.qrew.v1.service.models.audit import AuditAction
from com.qode.qrew.v1.service.models.user import KycStatus, User
from com.qode.qrew.v1.service.repositories.user import UserRepository
from com.qode.qrew.v1.service.schemas.admin import KycAction
from com.qode.qrew.v1.service.services.audit import AuditService
from com.qode.qrew.v1.service.services.notification import NotificationDispatcher

logger = structlog.get_logger(__name__)


class KycReviewError(DomainError):
    """Raised when a KYC review cannot be completed."""


class KycReviewService:
    def __init__(
        self,
        repo: UserRepository,
        notifier: NotificationDispatcher,
        audit: AuditService,
    ) -> None:
        self._repo = repo
        self._notifier = notifier
        self._audit = audit

    async def review(
        self,
        user_id: uuid.UUID,
        action: KycAction,
        reason: str | None,
    ) -> User:
        """Approve or reject a pending KYC submission and notify the user."""
        user = await self._repo.get_by_id(user_id)
        if user is None:
            raise KycReviewError("User not found", field="user_id")

        if user.kyc_status != KycStatus.pending:
            raise KycReviewError(
                f"KYC is not pending (current status: {user.kyc_status})",
                field="kyc_status",
            )

        new_status = (
            KycStatus.approved if action == KycAction.approve else KycStatus.rejected
        )
        user.kyc_status = new_status
        await self._repo.save(user)

        await self._notifier.send_kyc_status_update(
            user.email, user.full_name, new_status, reason
        )
        await logger.ainfo(
            "kyc_reviewed",
            user_id=str(user.id),
            action=action,
            status=new_status,
        )

        try:
            await self._audit.record(
                action=AuditAction.KYC_REVIEWED,
                entity_type="user",
                entity_id=str(user.id),
                payload={
                    "kyc_action": action,
                    "kyc_status": new_status,
                    "reason": reason,
                },
            )
        except Exception:
            await logger.awarning("audit_write_failed", action=AuditAction.KYC_REVIEWED)

        return user
