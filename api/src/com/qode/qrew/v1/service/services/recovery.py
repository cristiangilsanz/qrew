import hashlib
import uuid
from datetime import UTC, datetime, timedelta

import redis.asyncio as aioredis
import structlog
import webauthn
from webauthn.helpers.base64url_to_bytes import base64url_to_bytes
from webauthn.helpers.structs import (
    AuthenticatorAttestationResponse,
    AuthenticatorSelectionCriteria,
    PublicKeyCredentialType,
    RegistrationCredential,
    UserVerificationRequirement,
)

from com.qode.qrew.v1.service.core.errors import DomainError
from com.qode.qrew.v1.service.core.security import create_recovery_token
from com.qode.qrew.v1.service.models.audit import AuditAction
from com.qode.qrew.v1.service.models.passkey import PasskeyCredential
from com.qode.qrew.v1.service.models.user import User
from com.qode.qrew.v1.service.repositories.passkey import PasskeyCredentialRepository
from com.qode.qrew.v1.service.repositories.session import SessionRepository
from com.qode.qrew.v1.service.repositories.user import UserRepository
from com.qode.qrew.v1.service.schemas.auth import PasskeyRegistrationCompleteRequest
from com.qode.qrew.v1.service.services.audit import AuditService
from com.qode.qrew.v1.service.services.notification import NotificationDispatcher
from com.qode.qrew.v1.service.services.ocr import OcrError, OcrService
from com.qode.qrew.v1.service.settings import settings

logger = structlog.get_logger(__name__)

_CHALLENGE_PREFIX = "webauthn:recovery:challenge:"
_CHALLENGE_TTL_SECONDS = 300
_BLACKLIST_JTI_PREFIX = "blacklist:jti:"


class RecoveryError(DomainError):
    """Raised when an account recovery operation cannot be completed."""


class RecoveryService:
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
        """Verify identity via OCR + email and return (recovery_token, options_json).

        Returns (None, "") if no match — callers must return 200 regardless to
        prevent account enumeration.
        """
        try:
            id_number = self._ocr.extract_national_id(document)
        except OcrError:
            await self._audit_failed(None, "ocr_failed")
            return None, ""

        id_hash = hashlib.sha256(id_number.encode()).hexdigest()

        user = await self._user_repo.get_by_email(email.lower())
        if user is None or not user.is_active or user.national_id_hash != id_hash:
            await self._audit_failed(user.id if user else None, "identity_mismatch")
            return None, ""

        options = webauthn.generate_registration_options(
            rp_id=settings.rp_id,
            rp_name=settings.rp_name,
            user_id=str(user.id).encode(),
            user_name=user.email,
            user_display_name=user.full_name,
            authenticator_selection=AuthenticatorSelectionCriteria(
                user_verification=UserVerificationRequirement.REQUIRED,
            ),
        )
        await self._redis.set(
            _CHALLENGE_PREFIX + str(user.id),
            options.challenge,
            ex=_CHALLENGE_TTL_SECONDS,
        )

        token = create_recovery_token(str(user.id))

        await logger.ainfo("recovery_begin", user_id=str(user.id))
        try:
            await self._audit.record(
                action=AuditAction.RECOVERY_BEGIN,
                actor_id=user.id,
                entity_type="user",
                entity_id=str(user.id),
            )
        except Exception:
            await logger.awarning(
                "audit_write_failed", action=AuditAction.RECOVERY_BEGIN
            )

        return token, webauthn.options_to_json(options)

    async def complete(
        self,
        user: User,
        request: PasskeyRegistrationCompleteRequest,
    ) -> None:
        """Verify passkey attestation, revoke all sessions, register new credential."""
        raw_challenge: bytes | None = await self._redis.get(
            _CHALLENGE_PREFIX + str(user.id)
        )
        if raw_challenge is None:
            raise RecoveryError(
                "Recovery session expired. Please start again.", field=None
            )

        await self._redis.delete(_CHALLENGE_PREFIX + str(user.id))

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
            verification = webauthn.verify_registration_response(
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

        jtis = await self._session_repo.delete_all_by_user_id(user.id)
        now_ts = int(datetime.now(UTC).timestamp())
        exp_ts = now_ts + int(
            timedelta(days=settings.refresh_token_expire_days).total_seconds()
        )
        ttl = exp_ts - now_ts
        for jti in jtis:
            await self._redis.setex(_BLACKLIST_JTI_PREFIX + jti, ttl, "1")

        await self._passkey_repo.delete_all_by_user_id(user.id)

        await self._passkey_repo.create(
            PasskeyCredential(
                id=uuid.uuid4(),
                user_id=user.id,
                credential_id=verification.credential_id,
                public_key=verification.credential_public_key,
                sign_count=verification.sign_count,
                aaguid=str(verification.aaguid),
            )
        )

        try:
            await self._notifier.send_account_recovery(user.email, user.full_name)
        except Exception:
            await logger.awarning("notification_failed", action="account_recovery")

        await logger.ainfo("recovery_completed", user_id=str(user.id))
        try:
            await self._audit.record(
                action=AuditAction.RECOVERY_COMPLETED,
                actor_id=user.id,
                entity_type="user",
                entity_id=str(user.id),
            )
        except Exception:
            await logger.awarning(
                "audit_write_failed", action=AuditAction.RECOVERY_COMPLETED
            )

    async def _audit_failed(self, actor_id: uuid.UUID | None, reason: str) -> None:
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
