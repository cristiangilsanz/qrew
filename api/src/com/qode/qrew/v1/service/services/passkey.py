import uuid
from datetime import UTC, datetime

import redis.asyncio as aioredis
import structlog
import webauthn
from webauthn.helpers.base64url_to_bytes import base64url_to_bytes
from webauthn.helpers.structs import (
    AuthenticationCredential,
    AuthenticatorAssertionResponse,
    AuthenticatorAttestationResponse,
    AuthenticatorSelectionCriteria,
    PublicKeyCredentialDescriptor,
    PublicKeyCredentialType,
    RegistrationCredential,
    UserVerificationRequirement,
)

from com.qode.qrew.v1.service.core.errors import DomainError
from com.qode.qrew.v1.service.core.security import (
    create_access_token,
    create_refresh_token,
    create_setup_token,
    extract_jti,
)
from com.qode.qrew.v1.service.models.audit import AuditAction
from com.qode.qrew.v1.service.models.passkey import PasskeyCredential
from com.qode.qrew.v1.service.models.session import Session
from com.qode.qrew.v1.service.models.user import KycStatus, User
from com.qode.qrew.v1.service.repositories.passkey import PasskeyCredentialRepository
from com.qode.qrew.v1.service.repositories.session import SessionRepository
from com.qode.qrew.v1.service.repositories.user import UserRepository
from com.qode.qrew.v1.service.schemas.auth import (
    LoginResponse,
    PasskeyAuthenticationCompleteRequest,
    PasskeyRegistrationCompleteRequest,
)
from com.qode.qrew.v1.service.services.audit import AuditService
from com.qode.qrew.v1.service.settings import settings

logger = structlog.get_logger(__name__)

_CHALLENGE_TTL_SECONDS = 300
_CHALLENGE_PREFIX = "webauthn:challenge:"
_AUTH_CHALLENGE_PREFIX = "webauthn:auth:challenge:"


def _challenge_key(user_id: uuid.UUID) -> str:
    return f"{_CHALLENGE_PREFIX}{user_id}"


def _auth_challenge_key(user_id: uuid.UUID) -> str:
    return f"{_AUTH_CHALLENGE_PREFIX}{user_id}"


class PasskeyError(DomainError):
    """Raised when a passkey operation cannot be completed."""


class PasskeyService:
    def __init__(
        self,
        passkey_repo: PasskeyCredentialRepository,
        redis: aioredis.Redis,  # type: ignore[type-arg]
        user_repo: UserRepository,
        audit: AuditService,
        session_repo: SessionRepository | None = None,
    ) -> None:
        self._passkey_repo = passkey_repo
        self._redis = redis
        self._user_repo = user_repo
        self._audit = audit
        self._session_repo = session_repo

    async def begin_registration(self, user: User) -> str:
        """Generate WebAuthn registration options and cache the challenge."""
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
                detail=str(exc),
            )
            msg = (
                f"Passkey registration failed: {exc}"
                if settings.debug
                else "Passkey registration failed. Please try again."
            )
            raise PasskeyError(msg) from exc

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
        try:
            await self._audit.record(
                action=AuditAction.PASSKEY_REGISTERED,
                actor_id=user.id,
                entity_type="user",
                entity_id=str(user.id),
            )
        except Exception:
            await logger.awarning(
                "audit_write_failed", action=AuditAction.PASSKEY_REGISTERED
            )

    async def begin_authentication(self, email: str) -> str:
        """Generate WebAuthn assertion options and cache the challenge."""
        user = await self._user_repo.get_by_email(email)
        if user is None or not user.is_active or not user.email_verified:
            raise PasskeyError("No passkey found for this account")

        credentials = await self._passkey_repo.get_all_by_user_id(user.id)
        if not credentials:
            raise PasskeyError("No passkey registered for this account")

        allowed = [
            PublicKeyCredentialDescriptor(
                id=c.credential_id,
                type=PublicKeyCredentialType.PUBLIC_KEY,
            )
            for c in credentials
        ]
        options = webauthn.generate_authentication_options(
            rp_id=settings.rp_id,
            allow_credentials=allowed,
            user_verification=UserVerificationRequirement.REQUIRED,
        )
        await self._redis.set(
            _auth_challenge_key(user.id),
            options.challenge,
            ex=_CHALLENGE_TTL_SECONDS,
        )
        await logger.ainfo("passkey_authentication_begin", user_id=str(user.id))
        return webauthn.options_to_json(options)

    async def complete_authentication(
        self,
        request: PasskeyAuthenticationCompleteRequest,
        ip_address: str | None = None,
        user_agent: str | None = None,
        device_fingerprint: str | None = None,
    ) -> LoginResponse:
        """Verify the assertion response and return access tokens."""
        raw_id = base64url_to_bytes(request.raw_id)

        stored_credential = await self._passkey_repo.get_by_credential_id(raw_id)
        if stored_credential is None:
            await logger.awarning(
                "passkey_authentication_failed", reason="credential_not_found"
            )
            raise PasskeyError("Passkey not recognised")

        user = await self._user_repo.get_by_id(stored_credential.user_id)
        if user is None or not user.is_active:
            await logger.awarning(
                "passkey_authentication_failed",
                reason="user_not_found_or_inactive",
            )
            raise PasskeyError("Authentication failed")

        challenge_key = _auth_challenge_key(user.id)
        raw_challenge: bytes | None = await self._redis.get(challenge_key)
        if raw_challenge is None:
            await logger.awarning(
                "passkey_authentication_failed",
                reason="challenge_expired",
                user_id=str(user.id),
            )
            raise PasskeyError("Authentication session expired. Please start again.")

        await self._redis.delete(challenge_key)

        user_handle = (
            base64url_to_bytes(request.response.user_handle)
            if request.response.user_handle
            else None
        )
        credential = AuthenticationCredential(
            id=request.id,
            raw_id=raw_id,
            response=AuthenticatorAssertionResponse(
                client_data_json=base64url_to_bytes(request.response.client_data_json),
                authenticator_data=base64url_to_bytes(
                    request.response.authenticator_data
                ),
                signature=base64url_to_bytes(request.response.signature),
                user_handle=user_handle,
            ),
            type=PublicKeyCredentialType.PUBLIC_KEY,
        )

        try:
            verification = webauthn.verify_authentication_response(
                credential=credential,
                expected_challenge=raw_challenge,
                expected_rp_id=settings.rp_id,
                expected_origin=settings.rp_expected_origin,
                credential_current_sign_count=stored_credential.sign_count,
                credential_public_key=stored_credential.public_key,
                require_user_verification=True,
            )
        except Exception as exc:
            await logger.awarning(
                "passkey_authentication_failed",
                reason="verification_failed",
                user_id=str(user.id),
                detail=str(exc),
            )
            msg = (
                f"Passkey authentication failed: {exc}"
                if settings.debug
                else "Passkey authentication failed. Please try again."
            )
            raise PasskeyError(msg) from exc

        stored_credential.sign_count = verification.new_sign_count
        stored_credential.last_used_at = datetime.now(UTC)
        await self._passkey_repo.save(stored_credential)

        setup_complete = (
            user.phone_number_verified and user.kyc_status != KycStatus.not_submitted
        )

        if setup_complete:
            access_token = create_access_token(str(user.id))
            refresh_token = create_refresh_token(str(user.id))
            await self._persist_session(
                user.id, refresh_token, ip_address, user_agent, device_fingerprint
            )
            await logger.ainfo("passkey_authenticated", user_id=str(user.id))
            try:
                await self._audit.record(
                    action=AuditAction.PASSKEY_AUTHENTICATED,
                    actor_id=user.id,
                    entity_type="user",
                    entity_id=str(user.id),
                    payload={"setup_complete": True},
                )
            except Exception:
                await logger.awarning(
                    "audit_write_failed", action=AuditAction.PASSKEY_AUTHENTICATED
                )
            return LoginResponse(access_token=access_token, refresh_token=refresh_token)

        await logger.ainfo("passkey_authenticated_setup_required", user_id=str(user.id))
        try:
            await self._audit.record(
                action=AuditAction.PASSKEY_AUTHENTICATED,
                actor_id=user.id,
                entity_type="user",
                entity_id=str(user.id),
                payload={"setup_complete": False},
            )
        except Exception:
            await logger.awarning(
                "audit_write_failed", action=AuditAction.PASSKEY_AUTHENTICATED
            )
        return LoginResponse(
            access_token=create_setup_token(str(user.id)),
            setup_required=True,
        )

    async def _persist_session(
        self,
        user_id: uuid.UUID,
        refresh_token: str,
        ip_address: str | None,
        user_agent: str | None,
        device_fingerprint: str | None,
    ) -> None:
        if self._session_repo is None:
            return
        jti = extract_jti(refresh_token)
        if jti is None:
            return
        await self._session_repo.create(
            Session(
                id=uuid.uuid4(),
                user_id=user_id,
                jti=jti,
                ip_address=ip_address,
                user_agent=user_agent,
                device_fingerprint=device_fingerprint,
            )
        )
