import hashlib

import structlog
from cryptography.fernet import Fernet

from com.qode.qrew.v1.identity.core.errors import DomainError
from com.qode.qrew.v1.identity.services.storage import storage
from com.qode.qrew.v1.identity.models.audit.audit import AuditAction
from com.qode.qrew.v1.identity.models.auth.user import KycStatus, User
from com.qode.qrew.v1.identity.repositories.auth.user import UserRepository
from com.qode.qrew.v1.identity.services.audit import AuditService
from com.qode.qrew.v1.identity.services.notification import NotificationDispatcher
from com.qode.qrew.v1.identity.services.kyc.ocr import OcrError, OcrService
from com.qode.qrew.v1.identity.core.config import settings

logger = structlog.get_logger(__name__)

_MAX_FILE_BYTES = 10 * 1024 * 1024


class KycError(DomainError):
    """Raised when a KYC upload cannot be completed."""


class KycService:
    def __init__(
        self,
        repo: UserRepository,
        notifier: NotificationDispatcher,
        audit: AuditService,
        ocr: OcrService,
    ) -> None:
        self._repo = repo
        self._notifier = notifier
        self._audit = audit
        self._ocr = ocr

    async def upload(self, user: User, content: bytes) -> KycStatus:
        """Extract national ID via OCR, enforce uniqueness, and mark KYC pending."""
        if user.kyc_status == KycStatus.approved:
            await logger.awarning(
                "kyc_upload_failed", reason="already_approved", user_id=str(user.id)
            )
            raise KycError("KYC is already approved")
        if user.kyc_status == KycStatus.pending:
            await logger.awarning(
                "kyc_upload_failed",
                reason="already_pending",
                user_id=str(user.id),
            )
            raise KycError("KYC is already under review")

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

        try:
            id_number = self._ocr.extract_national_id(content)
        except OcrError as exc:
            await logger.awarning("kyc_upload_failed", reason="ocr_failed", user_id=str(user.id))
            raise KycError(str(exc)) from exc

        id_hash = hashlib.sha256(id_number.encode()).hexdigest()

        existing = await self._repo.get_by_national_id_hash(id_hash)
        if existing is not None and existing.id != user.id:
            await logger.awarning(
                "kyc_upload_failed",
                reason="duplicate_national_id",
                user_id=str(user.id),
            )
            raise KycError(
                "This national ID is already associated with another account",
                field="document",
            )

        fernet = Fernet(settings.national_id_encryption_key.encode())
        user.national_id_hash = id_hash
        user.national_id_number = fernet.encrypt(id_number.encode()).decode()
        previous_key = user.kyc_document_object_key
        object_key = await storage.put(
            kind="kyc",
            tenant=f"user:{user.id}",
            content=content,
            content_type="application/octet-stream",
        )
        user.kyc_document_object_key = object_key
        user.kyc_status = KycStatus.pending
        await self._repo.save(user)
        if previous_key:
            try:
                await storage.delete(previous_key)
            except Exception as exc:
                await logger.awarning(
                    "kyc_previous_doc_delete_failed", user_id=str(user.id), error=repr(exc)
                )

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
        except Exception as exc:
            await logger.awarning(
                "audit_write_failed", action=AuditAction.KYC_UPLOADED, error=repr(exc)
            )

        return user.kyc_status
