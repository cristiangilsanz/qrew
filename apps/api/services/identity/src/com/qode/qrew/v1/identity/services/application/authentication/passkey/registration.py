# registers a new passkey for a user
import uuid

import redis.asyncio as aioredis
import structlog
import webauthn
from webauthn.helpers.base64url_to_bytes import base64url_to_bytes
from webauthn.helpers.structs import (
    AuthenticatorAttestationResponse,
    AuthenticatorSelectionCriteria,
    PublicKeyCredentialType,
    RegistrationCredential,
    ResidentKeyRequirement,
    UserVerificationRequirement,
)
from webauthn.registration.verify_registration_response import VerifiedRegistration

from com.qode.qrew.v1.identity.models.audit import AuditAction
from com.qode.qrew.v1.identity.models.user import User
from com.qode.qrew.v1.identity.models.passkey import PasskeyCredential
from com.qode.qrew.v1.identity.repositories.passkey import (
    PasskeyCredentialRepository,
)
from com.qode.qrew.v1.identity.schemas.passkey import (
    PasskeyRegistrationCompleteRequest,
)
from com.qode.qrew.v1.identity.services.application.audit import AuditService
from com.qode.qrew.v1.identity.services.application.authentication.passkey.assertion import (
    CHALLENGE_TTL_SECONDS,
    PasskeyError,
    challenge_key,
)
from com.qode.qrew.v1.identity.core.config import settings

logger = structlog.get_logger(__name__)


class PasskeyRegistrationService:
    # stores the repository redis client and audit service the service uses
    def __init__(
        self,
        passkey_repo: PasskeyCredentialRepository,
        redis: aioredis.Redis,  # type: ignore[type-arg]
        audit: AuditService,
    ) -> None:
        self._passkey_repo = passkey_repo
        self._redis = redis
        self._audit = audit

    # refuses a second passkey, since an account holds exactly one
    async def _reject_if_already_registered(self, user: User) -> None:
        existing = await self._passkey_repo.get_all_by_user_id(user.id)
        if existing:
            await logger.awarning(
                "passkey_registration_failed",
                reason="already_registered",
                user_id=str(user.id),
            )
            raise PasskeyError("Passkey already registered.")

    # generates the webauthn options for a new resident key registration
    async def begin(self, user: User) -> str:
        await self._reject_if_already_registered(user)
        options = webauthn.generate_registration_options(
            rp_id=settings.rp_id,
            rp_name=settings.rp_name,
            user_id=str(user.id).encode(),
            user_name=user.email,
            user_display_name=user.full_name,
            authenticator_selection=AuthenticatorSelectionCriteria(
                resident_key=ResidentKeyRequirement.REQUIRED,
                user_verification=UserVerificationRequirement.REQUIRED,
            ),
        )
        await self._redis.set(challenge_key(user.id), options.challenge, ex=CHALLENGE_TTL_SECONDS)
        await logger.ainfo("passkey_registration_begin", user_id=str(user.id))
        return webauthn.options_to_json(options)

    # verifies the attestation and stores the new passkey credential
    async def complete(self, user: User, request: PasskeyRegistrationCompleteRequest) -> None:
        await self._reject_if_already_registered(user)
        raw_challenge = await self._consume_challenge(user)
        verification = self._verify_attestation(user, raw_challenge, request)
        await self._passkey_repo.create(
            PasskeyCredential(
                id=uuid.uuid4(),
                user_id=user.id,
                credential_id=verification.credential_id,
                public_key=verification.credential_public_key,
                sign_count=verification.sign_count,
                aaguid=str(verification.aaguid),
                name="Default",
            )
        )
        await logger.ainfo("passkey_registered", user_id=str(user.id))
        await self._audit_safe(user.id)

    # reads and deletes the pending registration challenge
    async def _consume_challenge(self, user: User) -> bytes:
        raw_challenge: bytes | None = await self._redis.get(challenge_key(user.id))
        if raw_challenge is None:
            await logger.awarning(
                "passkey_registration_failed",
                reason="challenge_expired",
                user_id=str(user.id),
            )
            raise PasskeyError("Registration session expired.")
        await self._redis.delete(challenge_key(user.id))
        return raw_challenge

    # verifies the webauthn registration response against the challenge
    def _verify_attestation(
        self,
        user: User,
        raw_challenge: bytes,
        request: PasskeyRegistrationCompleteRequest,
    ) -> VerifiedRegistration:
        expected_origins: str | list[str] = (
            [settings.rp_expected_origin] + settings.rp_expected_origins
            if settings.rp_expected_origins
            else settings.rp_expected_origin
        )
        try:
            credential = RegistrationCredential(
                id=request.id,
                raw_id=base64url_to_bytes(request.raw_id),
                response=AuthenticatorAttestationResponse(
                    client_data_json=base64url_to_bytes(request.response.client_data_json),
                    attestation_object=base64url_to_bytes(request.response.attestation_object),
                ),
                type=PublicKeyCredentialType.PUBLIC_KEY,
            )
            return webauthn.verify_registration_response(
                credential=credential,
                expected_challenge=raw_challenge,
                expected_rp_id=settings.rp_id,
                expected_origin=expected_origins,
                require_user_verification=True,
            )
        except Exception as exc:
            msg = (
                f"Passkey registration failed: {exc}"
                if settings.debug
                else "Passkey registration failed. Please try again."
            )
            raise PasskeyError(msg) from exc

    # records the passkey registration without letting a failure interrupt it
    async def _audit_safe(self, user_id: uuid.UUID) -> None:
        try:
            await self._audit.record(
                action=AuditAction.PASSKEY_REGISTERED,
                actor_id=user_id,
                entity_type="user",
                entity_id=str(user_id),
            )
        except Exception as exc:
            await logger.awarning(
                "audit_write_failed", action=AuditAction.PASSKEY_REGISTERED, error=repr(exc)
            )
