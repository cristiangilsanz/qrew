import uuid

import redis.asyncio as aioredis
import structlog
import webauthn
from webauthn.helpers.base64url_to_bytes import base64url_to_bytes
from webauthn.helpers.structs import (
    AuthenticatorAttestationResponse,
    PublicKeyCredentialType,
    RegistrationCredential,
)

from com.qode.qrew.v1.service.core.errors import DomainError
from com.qode.qrew.v1.service.models.passkey import PasskeyCredential
from com.qode.qrew.v1.service.models.user import User
from com.qode.qrew.v1.service.repositories.passkey import PasskeyCredentialRepository
from com.qode.qrew.v1.service.schemas.auth import PasskeyRegistrationCompleteRequest
from com.qode.qrew.v1.service.settings import settings

logger = structlog.get_logger(__name__)

_CHALLENGE_TTL_SECONDS = 300
_CHALLENGE_PREFIX = "webauthn:challenge:"


def _challenge_key(user_id: uuid.UUID) -> str:
    return f"{_CHALLENGE_PREFIX}{user_id}"


class PasskeyError(DomainError):
    """Raised when a passkey operation cannot be completed."""


class PasskeyService:
    def __init__(
        self,
        passkey_repo: PasskeyCredentialRepository,
        redis: aioredis.Redis,  # type: ignore[type-arg]
    ) -> None:
        self._passkey_repo = passkey_repo
        self._redis = redis

    async def begin_registration(self, user: User) -> str:
        """Generate WebAuthn registration options and cache the challenge."""
        options = webauthn.generate_registration_options(
            rp_id=settings.rp_id,
            rp_name=settings.rp_name,
            user_id=str(user.id).encode(),
            user_name=user.email,
            user_display_name=user.full_name,
        )
        await self._redis.set(
            _challenge_key(user.id),
            options.challenge,
            ex=_CHALLENGE_TTL_SECONDS,
        )
        await logger.ainfo("passkey_registration_begin", user_id=str(user.id))
        return webauthn.options_to_json(options)

    async def complete_registration(
        self,
        user: User,
        request: PasskeyRegistrationCompleteRequest,
    ) -> None:
        """Verify the attestation response and persist the passkey credential."""
        raw_challenge: bytes | None = await self._redis.get(_challenge_key(user.id))
        if raw_challenge is None:
            await logger.awarning(
                "passkey_registration_failed",
                reason="challenge_expired",
                user_id=str(user.id),
            )
            raise PasskeyError("Registration session expired. Please start again.")

        await self._redis.delete(_challenge_key(user.id))

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
            await logger.awarning(
                "passkey_registration_failed",
                reason="verification_failed",
                user_id=str(user.id),
            )
            raise PasskeyError(
                "Passkey registration failed. Please try again."
            ) from exc

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
        await logger.ainfo("passkey_registered", user_id=str(user.id))
