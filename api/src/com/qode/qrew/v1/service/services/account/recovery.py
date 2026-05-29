import hashlib
import uuid
from datetime import timedelta

import redis.asyncio as aioredis
import structlog
import webauthn
from webauthn.helpers.base64url_to_bytes import base64url_to_bytes
from webauthn.helpers.structs import (
    AuthenticatorAttestationResponse,
    AuthenticatorSelectionCriteria,
    PublicKeyCredentialCreationOptions,
    PublicKeyCredentialType,
    RegistrationCredential,
    UserVerificationRequirement,
)
from webauthn.registration.verify_registration_response import VerifiedRegistration

from com.qode.qrew.v1.service.core.auth.security import create_recovery_token
from com.qode.qrew.v1.service.core.infra.errors import DomainError
from com.qode.qrew.v1.service.models.audit.audit import AuditAction
from com.qode.qrew.v1.service.models.auth.user import User
from com.qode.qrew.v1.service.models.passkey.passkey import PasskeyCredential
from com.qode.qrew.v1.service.repositories.auth.session import SessionRepository
from com.qode.qrew.v1.service.repositories.auth.user import UserRepository
from com.qode.qrew.v1.service.repositories.passkey.passkey import (
    PasskeyCredentialRepository,
)
from com.qode.qrew.v1.service.schemas.passkey.passkey import (
    PasskeyRegistrationCompleteRequest,
)
from com.qode.qrew.v1.service.services.audit import AuditService
from com.qode.qrew.v1.service.services.infra.notification import NotificationDispatcher
from com.qode.qrew.v1.service.services.kyc.ocr import OcrError, OcrService
from com.qode.qrew.v1.service.settings import settings

logger = structlog.get_logger(__name__)

_CHALLENGE_PREFIX = "webauthn:recovery:challenge:"
_CHALLENGE_TTL_SECONDS = 300
_BLACKLIST_JTI_PREFIX = "blacklist:jti:"


class RecoveryError(DomainError):
    """Raised when an account recovery operation cannot be completed."""


class RecoveryService:
    """Account recovery via national-ID verification and passkey re-enrolment."""

    def __init__(
        self,
        user_repo: UserRepository,
        passkey_repo: PasskeyCredentialRepository,
        session_repo: SessionRepository,
        redis: aioredis.Redis,  # type: ignore[type-arg]
        notifier: NotificationDispatcher,
        audit: AuditService,
        ocr: OcrService,
    ) -> None:
        self._user_repo = user_repo
        self._passkey_repo = passkey_repo
        self._session_repo = session_repo
        self._redis = redis
        self._notifier = notifier
        self._audit = audit
        self._ocr = ocr

    async def begin(self, email: str, document: bytes) -> tuple[str | None, str]:
        """Begin account recovery by verifying identity from a document."""
        user = await self._verify_identity(email, document)
        if user is None:
            return None, ""

        options = self._generate_registration_options(user)
        await self._redis.set(
            _CHALLENGE_PREFIX + str(user.id),
            options.challenge,
            ex=_CHALLENGE_TTL_SECONDS,
        )
        token = create_recovery_token(str(user.id))

        await logger.ainfo("recovery_begin", user_id=str(user.id))
        await self._audit_safe(AuditAction.RECOVERY_BEGIN, user.id)
        return token, webauthn.options_to_json(options)

    async def complete(
        self,
        user: User,
        request: PasskeyRegistrationCompleteRequest,
    ) -> None:
        """Complete account recovery by registering a fresh passkey."""
        raw_challenge = await self._consume_challenge(user.id)
        verification = self._verify_attestation(raw_challenge, request)
        await self._kill_sessions(user.id)
        await self._replace_passkey(user.id, verification)
        await self._notify_recovery(user)
        await logger.ainfo("recovery_completed", user_id=str(user.id))
        await self._audit_safe(AuditAction.RECOVERY_COMPLETED, user.id)

    async def _verify_identity(self, email: str, document: bytes) -> User | None:
        """Match the document holder to the account or audit a failure."""
        try:
            id_number = self._ocr.extract_national_id(document)
        except OcrError:
            await self._audit_failed(None, "ocr_failed")
            return None

        id_hash = hashlib.sha256(id_number.encode()).hexdigest()
        user = await self._user_repo.get_by_email(email.lower())
        if user is None or not user.is_active or user.national_id_hash != id_hash:
            await self._audit_failed(user.id if user else None, "identity_mismatch")
            return None
        return user

    def _generate_registration_options(
        self, user: User
    ) -> PublicKeyCredentialCreationOptions:
        """Build WebAuthn registration options for the recovering user."""
        return webauthn.generate_registration_options(
            rp_id=settings.rp_id,
            rp_name=settings.rp_name,
            user_id=str(user.id).encode(),
            user_name=user.email,
            user_display_name=user.full_name,
            authenticator_selection=AuthenticatorSelectionCriteria(
                user_verification=UserVerificationRequirement.REQUIRED,
            ),
        )

    async def _consume_challenge(self, user_id: uuid.UUID) -> bytes:
        """Pop and return the cached recovery challenge."""
        key = _CHALLENGE_PREFIX + str(user_id)
        raw_challenge: bytes | None = await self._redis.get(key)
        if raw_challenge is None:
            raise RecoveryError(
                "Recovery session expired. Please start again.", field=None
            )
        await self._redis.delete(key)
        return raw_challenge

    def _verify_attestation(
        self,
        raw_challenge: bytes,
        request: PasskeyRegistrationCompleteRequest,
    ) -> VerifiedRegistration:
        """Verify the passkey attestation submitted during recovery."""
        credential = RegistrationCredential(
            id=request.id,
            raw_id=base64url_to_bytes(request.raw_id),
            response=AuthenticatorAttestationResponse(
                client_data_json=base64url_to_bytes(request.response.client_data_json),
                attestation_object=base64url_to_bytes(
                    request.response.attestation_object
                ),
            ),
            type=PublicKeyCredentialType.PUBLIC_KEY,
        )
        try:
            return webauthn.verify_registration_response(
                credential=credential,
                expected_challenge=raw_challenge,
                expected_rp_id=settings.rp_id,
                expected_origin=settings.rp_expected_origin,
                require_user_verification=True,
            )
        except Exception as exc:
            msg = (
                f"Passkey registration failed: {exc}"
                if settings.debug
                else "Passkey registration failed. Please try again."
            )
            raise RecoveryError(msg) from exc

    async def _kill_sessions(self, user_id: uuid.UUID) -> None:
        """Revoke every active session for the recovering user."""
        jtis = await self._session_repo.delete_all_by_user_id(user_id)
        ttl = int(timedelta(days=settings.refresh_token_expire_days).total_seconds())
        for jti in jtis:
            await self._redis.setex(_BLACKLIST_JTI_PREFIX + jti, ttl, "1")

    async def _replace_passkey(
        self, user_id: uuid.UUID, verification: VerifiedRegistration
    ) -> None:
        """Wipe existing passkeys and persist the freshly registered credential."""
        await self._passkey_repo.delete_all_by_user_id(user_id)
        await self._passkey_repo.create(
            PasskeyCredential(
                id=uuid.uuid4(),
                user_id=user_id,
                credential_id=verification.credential_id,
                public_key=verification.credential_public_key,
                sign_count=verification.sign_count,
                aaguid=str(verification.aaguid),
            )
        )

    async def _notify_recovery(self, user: User) -> None:
        """Send the recovery completion notification without propagating errors."""
        try:
            await self._notifier.send_account_recovery(user.email, user.full_name)
        except Exception:
            await logger.awarning("notification_failed", action="account_recovery")

    async def _audit_failed(self, actor_id: uuid.UUID | None, reason: str) -> None:
        """Record a recovery failure audit event."""
        await logger.awarning("recovery_failed", reason=reason)
        try:
            await self._audit.record(
                action=AuditAction.RECOVERY_FAILED,
                actor_id=actor_id,
                entity_type="user",
                entity_id=str(actor_id) if actor_id else None,
                payload={"reason": reason},
            )
        except Exception:
            await logger.awarning(
                "audit_write_failed", action=AuditAction.RECOVERY_FAILED
            )

    async def _audit_safe(self, action: AuditAction, user_id: uuid.UUID) -> None:
        """Record a successful recovery audit event without raising."""
        try:
            await self._audit.record(
                action=action,
                actor_id=user_id,
                entity_type="user",
                entity_id=str(user_id),
            )
        except Exception:
            await logger.awarning("audit_write_failed", action=action)
