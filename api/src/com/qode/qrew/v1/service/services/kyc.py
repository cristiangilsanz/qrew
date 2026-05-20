import hashlib

import structlog

from com.qode.qrew.v1.service.core.errors import DomainError
from com.qode.qrew.v1.service.models.audit import AuditAction
from com.qode.qrew.v1.service.models.user import KycStatus, User
from com.qode.qrew.v1.service.repositories.user import UserRepository
from com.qode.qrew.v1.service.services.audit import AuditService
from com.qode.qrew.v1.service.services.notification import NotificationDispatcher
from com.qode.qrew.v1.service.settings import settings

logger = structlog.get_logger(__name__)

_MAX_FILE_BYTES = 10 * 1024 * 1024  # 10 MB


class KycError(DomainError):
    """Raised when a KYC upload cannot be completed."""


class KycService:
    def __init__(
        self,
        repo: UserRepository,
        notifier: NotificationDispatcher,
        audit: AuditService,
    ) -> None:
        self._repo = repo
        self._notifier = notifier
        self._audit = audit

    async def upload(self, user: User, content: bytes) -> KycStatus:
        """Hash the document, mark KYC as pending (or auto-approve if enabled)."""
        if len(content) == 0:
            await logger.awarning(
                "kyc_upload_failed", reason="empty_document", user_id=str(user.id)
            )
            raise KycError("Document cannot be empty")
        if len(content) > _MAX_FILE_BYTES:
            await logger.awarning(
                "kyc_upload_failed", reason="document_too_large", user_id=str(user.id)
            )
            raise KycError("Document exceeds the maximum allowed size of 10 MB")

        user.national_id_hash = hashlib.sha256(content).hexdigest()
        user.kyc_status = KycStatus.pending
        await self._repo.save(user)

        if settings.kyc_auto_approve:
            user.kyc_status = KycStatus.approved
            await self._repo.save(user)
            await self._notifier.send_kyc_status_update(
                user.email, user.full_name, KycStatus.approved, None
            )
            await logger.ainfo("kyc_auto_approved", user_id=str(user.id))
        else:
            await logger.ainfo("kyc_submitted", user_id=str(user.id))

        try:
            await self._audit.record(
                action=AuditAction.KYC_UPLOADED,
                actor_id=user.id,
                entity_type="user",
                entity_id=str(user.id),
                payload={"kyc_status": user.kyc_status},
            )
        except Exception:
            await logger.awarning("audit_write_failed", action=AuditAction.KYC_UPLOADED)

        return user.kyc_status
