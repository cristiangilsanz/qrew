from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from com.qode.qrew.v1.identity.core.infra.database import get_db
from com.qode.qrew.v1.identity.core.registration.captcha import CaptchaService
from com.qode.qrew.v1.identity.repositories.auth.user import UserRepository
from com.qode.qrew.v1.identity.services.audit import AuditService
from com.qode.qrew.v1.identity.services.infra.notification import NotificationDispatcher
from com.qode.qrew.v1.identity.services.registration.registration import (
    RegistrationService,
)
from com.qode.qrew.v1.identity.services.registration.resend_verification import (
    ResendEmailVerificationService,
    ResendPhoneOtpService,
)
from com.qode.qrew.v1.identity.services.registration.verification import (
    EmailVerificationService,
    PhoneVerificationService,
)

from .shared import (
    get_captcha_service,
    get_notification_service,
)


def get_registration_service(
    db: AsyncSession = Depends(get_db),
    notifier: NotificationDispatcher = Depends(get_notification_service),
    captcha: CaptchaService = Depends(get_captcha_service),
) -> RegistrationService:
    """Build the registration service."""
    return RegistrationService(UserRepository(db), notifier, captcha, AuditService())


def get_email_verification_service(
    db: AsyncSession = Depends(get_db),
) -> EmailVerificationService:
    """Build the email verification service."""
    return EmailVerificationService(UserRepository(db), AuditService())


def get_phone_verification_service(
    db: AsyncSession = Depends(get_db),
) -> PhoneVerificationService:
    """Build the phone verification service."""
    return PhoneVerificationService(UserRepository(db), AuditService())


def get_resend_email_verification_service(
    db: AsyncSession = Depends(get_db),
    notifier: NotificationDispatcher = Depends(get_notification_service),
) -> ResendEmailVerificationService:
    """Build the resend email verification service."""
    return ResendEmailVerificationService(UserRepository(db), notifier)


def get_resend_phone_otp_service(
    db: AsyncSession = Depends(get_db),
    notifier: NotificationDispatcher = Depends(get_notification_service),
) -> ResendPhoneOtpService:
    """Build the resend phone otp service."""
    return ResendPhoneOtpService(UserRepository(db), notifier)
