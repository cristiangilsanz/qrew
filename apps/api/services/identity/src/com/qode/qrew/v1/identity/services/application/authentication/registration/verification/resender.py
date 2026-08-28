# resends an email or phone verification code without disclosing whether the account exists
import structlog

from com.qode.qrew.v1.identity.core.utils import pii as pii_crypto
from com.qode.qrew.v1.identity.services.application.authentication.token.security import (
    email_verification_token_expiry,
    generate_otp,
    generate_token,
    phone_number_otp_expiry,
)
from com.qode.qrew.v1.identity.core.errors import DomainError
from com.qode.qrew.v1.identity.repositories.user import UserRepository
from com.qode.qrew.v1.identity.services.application.notification.dispatcher import (
    NotificationDispatcher,
)

logger = structlog.get_logger(__name__)


class ResendError(DomainError):
    pass


class ResendEmailVerificationService:
    # stores the repository and notifier the service uses
    def __init__(self, repo: UserRepository, notifier: NotificationDispatcher) -> None:
        self._repo = repo
        self._notifier = notifier

    # resends the email verification link if the account is not already verified
    async def resend(self, email: str) -> None:
        user = await self._repo.get_by_email(email)

        if user is None:
            await logger.awarning("resend_email_skipped", reason="user_not_found")
            return
        if user.email_verified:
            await logger.awarning(
                "resend_email_skipped",
                reason="already_verified",
                user_id=str(user.id),
            )
            return

        token = generate_token()
        user.email_verification_token = pii_crypto.hash_lookup(token)
        user.email_verification_token_expires_at = email_verification_token_expiry()
        await self._repo.save(user)

        await self._notifier.send_email_verification_link(user.email, user.full_name, token)
        await logger.ainfo("email_verification_resent", user_id=str(user.id))


class ResendPhoneOtpService:
    # stores the repository and notifier the service uses
    def __init__(self, repo: UserRepository, notifier: NotificationDispatcher) -> None:
        self._repo = repo
        self._notifier = notifier

    # resends the phone verification otp if the account is not already verified
    async def resend(self, phone_number: str) -> None:
        user = await self._repo.get_by_phone_number(phone_number)

        if user is None:
            await logger.awarning("resend_otp_skipped", reason="user_not_found")
            return
        if user.phone_number_verified:
            await logger.awarning(
                "resend_otp_skipped",
                reason="already_verified",
                user_id=str(user.id),
            )
            return

        otp = generate_otp()
        user.phone_number_otp = pii_crypto.hash_lookup(otp)
        user.phone_number_otp_expires_at = phone_number_otp_expiry()
        await self._repo.save(user)

        await self._notifier.send_sms_otp(user.phone_number, otp)
        await logger.ainfo("phone_otp_resent", user_id=str(user.id))
