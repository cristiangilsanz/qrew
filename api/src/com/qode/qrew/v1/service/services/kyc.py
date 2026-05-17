import hashlib

import structlog

from com.qode.qrew.v1.service.core.errors import DomainError
from com.qode.qrew.v1.service.models.user import KycStatus, User
from com.qode.qrew.v1.service.repositories.user import UserRepository

logger = structlog.get_logger(__name__)

_MAX_FILE_BYTES = 10 * 1024 * 1024  # 10 MB


class KycError(DomainError):
    """Raised when a KYC upload cannot be completed."""


class KycService:
    def __init__(self, repo: UserRepository) -> None:
        self._repo = repo

    async def upload(self, user: User, content: bytes) -> None:
        """Hash the document and mark the user's KYC status as pending."""
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

        await logger.ainfo("kyc_submitted", user_id=str(user.id))
