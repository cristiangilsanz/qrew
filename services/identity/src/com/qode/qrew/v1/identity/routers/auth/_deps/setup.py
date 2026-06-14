from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from com.qode.qrew.v1.identity.database import get_db
from com.qode.qrew.v1.identity.repositories.auth.session import SessionRepository
from com.qode.qrew.v1.identity.repositories.auth.user import UserRepository
from com.qode.qrew.v1.identity.repositories.passkey.passkey import (
    PasskeyCredentialRepository,
)
from com.qode.qrew.v1.identity.services.audit import AuditService
from com.qode.qrew.v1.identity.services.infra.notification import NotificationDispatcher
from com.qode.qrew.v1.identity.services.kyc.kyc import KycService
from com.qode.qrew.v1.identity.services.kyc.ocr import OcrService
from com.qode.qrew.v1.identity.services.registration.complete_setup import (
    CompleteSetupService,
)

from .shared import get_notification_service, get_ocr_service


def get_kyc_service(
    db: AsyncSession = Depends(get_db),
    notifier: NotificationDispatcher = Depends(get_notification_service),
    ocr: OcrService = Depends(get_ocr_service),
) -> KycService:
    """Build the KYC service."""
    return KycService(UserRepository(db), notifier, AuditService(), ocr)


def get_complete_setup_service(
    db: AsyncSession = Depends(get_db),
) -> CompleteSetupService:
    """Build the complete-setup service."""
    return CompleteSetupService(
        UserRepository(db),
        PasskeyCredentialRepository(db),
        AuditService(),
        SessionRepository(db),
    )
