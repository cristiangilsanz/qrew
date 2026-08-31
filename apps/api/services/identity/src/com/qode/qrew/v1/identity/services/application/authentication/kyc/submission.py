# submits a national identity document for kyc review
import hashlib

import structlog
from cryptography.fernet import Fernet
from security import DocumentType, validate_document

from com.qode.qrew.v1.identity.core.errors import DomainError
from com.qode.qrew.v1.identity.services.application.storage import storage
from com.qode.qrew.v1.identity.models.audit import AuditAction
from com.qode.qrew.v1.identity.models.user import KycOcrResult, KycStatus, User
from com.qode.qrew.v1.identity.repositories.user import UserRepository
from com.qode.qrew.v1.identity.services.application.audit import AuditService
from com.qode.qrew.v1.identity.services.application.notification.dispatcher import (
    NotificationDispatcher,
)
from com.qode.qrew.v1.identity.services.application.authentication.kyc.ocr import (
    OcrError,
    OcrService,
)
from com.qode.qrew.v1.identity.core.config import settings

logger = structlog.get_logger(__name__)

_MAX_FILE_BYTES = 10 * 1024 * 1024


class KycError(DomainError):
    pass


class KycService:
    # stores the repository notifier audit service and ocr service the service uses
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

    # records the declared document stores its image and marks kyc pending
    async def upload(
        self,
        user: User,
        content: bytes,
        *,
        document_type: DocumentType,
        document_number: str,
    ) -> KycStatus:
        if user.kyc_status == KycStatus.approved:
            await logger.awarning(
                "kyc_upload_failed", reason="already_approved", user_id=str(user.id)
            )
            raise KycError("Verification already approved.")
        if user.kyc_status == KycStatus.pending:
            await logger.awarning(
                "kyc_upload_failed",
                reason="already_pending",
                user_id=str(user.id),
            )
            raise KycError("Verification already under review.")

        if len(content) == 0:
            await logger.awarning(
                "kyc_upload_failed", reason="empty_document", user_id=str(user.id)
            )
            raise KycError("Document empty.")
        if len(content) > _MAX_FILE_BYTES:
            await logger.awarning(
                "kyc_upload_failed", reason="document_too_large", user_id=str(user.id)
            )
            raise KycError("Document exceeds the maximum size of 10 MB.")

        try:
            id_number = validate_document(document_number, document_type)
        except ValueError as exc:
            await logger.awarning(
                "kyc_upload_failed", reason="document_rejected", user_id=str(user.id)
            )
            raise KycError(str(exc), field="document_number") from exc

        ocr_result = await self._read_back(user, content, document_type, id_number)

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
        user.national_id_type = str(document_type)
        previous_key = user.kyc_document_object_key
        object_key = await storage.put(
            kind="kyc",
            tenant=f"user:{user.id}",
            content=content,
            content_type="application/octet-stream",
        )
        user.kyc_document_object_key = object_key
        user.kyc_ocr_result = str(ocr_result)
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
                user.email, user.full_name, KycStatus.approved
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
                payload={"kyc_status": user.kyc_status, "ocr_result": user.kyc_ocr_result},
            )
        except Exception as exc:
            await logger.awarning(
                "audit_write_failed", action=AuditAction.KYC_UPLOADED, error=repr(exc)
            )

        return user.kyc_status

    # reads the number back off the image and reports how it compared, leaving a
    # trace of every outcome so a reviewer knows where the automatic check stopped
    async def _read_back(
        self,
        user: User,
        content: bytes,
        document_type: DocumentType,
        id_number: str,
    ) -> KycOcrResult:
        if document_type not in {DocumentType.dni, DocumentType.nie}:
            await logger.ainfo(
                "kyc_ocr_skipped", user_id=str(user.id), document_type=str(document_type)
            )
            return KycOcrResult.not_applicable

        try:
            scanned = self._ocr.extract_national_id(content)
        except OcrError:
            await logger.awarning(
                "kyc_ocr_unreadable", user_id=str(user.id), document_type=str(document_type)
            )
            return KycOcrResult.unreadable

        if scanned != id_number:
            await logger.awarning(
                "kyc_document_mismatch",
                user_id=str(user.id),
                document_type=str(document_type),
            )
            return KycOcrResult.mismatch

        await logger.ainfo("kyc_ocr_match", user_id=str(user.id))
        return KycOcrResult.match
