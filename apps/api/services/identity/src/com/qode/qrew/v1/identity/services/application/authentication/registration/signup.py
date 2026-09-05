# creates a new account after validating its captcha email phone and password
import uuid
from datetime import UTC, datetime

import structlog

from outbox import record as record_event

from com.qode.qrew.v1.identity.models.event_outbox import EventOutbox
from com.qode.qrew.v1.identity.services.application.authentication.token.security import (
    email_verification_token_expiry,
    generate_otp,
    generate_token,
    hash_password,
    is_password_pwned,
    phone_number_otp_expiry,
)
from com.qode.qrew.v1.identity.core.errors import DomainError
from observability import traced
from com.qode.qrew.v1.identity.services.application.authentication.registration.captcha import (
    CaptchaService,
)
from com.qode.qrew.v1.identity.models.audit import AuditAction
from com.qode.qrew.v1.identity.core.utils import pii as pii_crypto
from com.qode.qrew.v1.identity.models.user import User
from com.qode.qrew.v1.identity.repositories.user import UserRepository
from com.qode.qrew.v1.identity.schemas.registration import (
    RegisterRequest,
    RegisterResponse,
)
from com.qode.qrew.v1.identity.services.application.audit import AuditService
from com.qode.qrew.v1.identity.services.application.notification.dispatcher import (
    NotificationDispatcher,
)

logger = structlog.get_logger(__name__)


class RegistrationError(DomainError):
    pass


# builds the new user row with its hashed password and verification tokens
def _build_user(
    request: RegisterRequest,
    ip_address: str,
    device_fingerprint: str | None,
    email_token: str,
    phone_otp: str,
) -> User:
    now = datetime.now(UTC)
    return User(
        id=uuid.uuid4(),
        full_name=request.full_name,
        email=request.email,
        phone_number=request.phone_number,
        hashed_password=hash_password(request.password),
        email_verified=False,
        phone_number_verified=False,
        email_verification_token=pii_crypto.hash_lookup(email_token),
        email_verification_token_expires_at=email_verification_token_expiry(),
        phone_number_otp=pii_crypto.hash_lookup(phone_otp),
        phone_number_otp_expires_at=phone_number_otp_expiry(),
        terms_accepted_at=now,
        registration_ip=ip_address,
        device_fingerprint=device_fingerprint,
        is_active=True,
    )


class RegistrationService:
    # stores the repository notifier captcha service and audit service the service uses
    def __init__(
        self,
        repo: UserRepository,
        notifier: NotificationDispatcher,
        captcha: CaptchaService,
        audit: AuditService,
    ) -> None:
        self._repo = repo
        self._notifier = notifier
        self._captcha = captcha
        self._audit = audit

    # validates the request creates the account and sends its verification codes
    @traced("auth.register")
    async def register(
        self,
        request: RegisterRequest,
        ip_address: str,
        device_fingerprint: str | None = None,
    ) -> RegisterResponse:
        await self._assert_captcha_valid(request.captcha_token, ip_address)

        await self._assert_email_available(request.email)
        await self._assert_phone_available(request.phone_number)
        await self._assert_password_not_breached(request.password)

        email_token = generate_token()
        phone_otp = generate_otp()
        user = _build_user(request, ip_address, device_fingerprint, email_token, phone_otp)
        created = await self._repo.create(user)

        await self._dispatch_verifications(created, email_token, phone_otp)

        await logger.ainfo(
            "user_registered",
            user_id=str(created.id),
            registration_ip=ip_address,
        )

        try:
            await self._audit.record(
                action=AuditAction.REGISTER,
                actor_id=created.id,
                entity_type="user",
                entity_id=str(created.id),
                ip_address=ip_address,
                payload={"email": created.email},
            )
        except Exception as exc:
            await logger.awarning(
                "audit_write_failed", action=AuditAction.REGISTER, error=repr(exc)
            )

        await self._publish_registered(created)

        return RegisterResponse(
            id=str(created.id),
            message="Registration successful. Check your email to verify your account.",
        )

    # leaves in the outbox that a user registered
    async def _publish_registered(self, user: User) -> None:
        from datetime import UTC, datetime

        await record_event(
            self._repo.session,
            EventOutbox,
            subject="identity.user.registered.v1",
            aggregate_type="user",
            aggregate_id=str(user.id),
            actor_id=str(user.id),
            data={
                "user_id": str(user.id),
                "registered_at": user.created_at.isoformat()
                if getattr(user, "created_at", None)
                else datetime.now(UTC).isoformat(),
                "phone_e164": user.phone_number,
            },
        )

    # rejects the request unless the captcha passes
    async def _assert_captcha_valid(self, token: str, ip_address: str) -> None:
        await self._captcha.verify(token, ip_address)

    # rejects the request if the email is already registered
    async def _assert_email_available(self, email: str) -> None:
        if await self._repo.exists_by_email(email):
            await logger.awarning("registration_failed", reason="email_taken")
            raise RegistrationError("Email already registered.", field="email")

    # rejects the request if the phone number is already registered
    async def _assert_phone_available(self, phone_number: str) -> None:
        if await self._repo.exists_by_phone(phone_number):
            await logger.awarning("registration_failed", reason="phone_number_taken")
            raise RegistrationError("Phone number already registered.", field="phone_number")

    # rejects the request if the password appears in a known breach
    async def _assert_password_not_breached(self, password: str) -> None:
        if await is_password_pwned(password):
            await logger.awarning("registration_failed", reason="password_breached")
            raise RegistrationError(
                "This password has appeared in a known data breach. Choose a different one",
                field="password",
            )

    # sends the email and phone verification codes
    async def _dispatch_verifications(self, user: User, email_token: str, phone_otp: str) -> None:
        await self._notifier.send_email_verification_link(
            user.email,
            user.full_name,
            email_token,
        )
        await self._notifier.send_sms_otp(
            user.phone_number,
            phone_otp,
        )
