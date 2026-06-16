import uuid
from datetime import UTC, datetime

import redis.asyncio as aioredis
import structlog
import webauthn
from webauthn.authentication.verify_authentication_response import (
    VerifiedAuthentication,
)
from webauthn.helpers.base64url_to_bytes import base64url_to_bytes

from com.qode.qrew.v1.identity.services.auth.security import (
    create_access_token,
    create_refresh_token,
    create_setup_token,
    extract_jti,
)
from com.qode.qrew.v1.identity.models.audit.audit import AuditAction
from com.qode.qrew.v1.identity.models.auth.session import Session
from com.qode.qrew.v1.identity.models.auth.user import KycStatus, User
from com.qode.qrew.v1.identity.models.passkey.passkey import PasskeyCredential
from com.qode.qrew.v1.identity.repositories.auth.session import SessionRepository
from com.qode.qrew.v1.identity.repositories.auth.user import UserRepository
from com.qode.qrew.v1.identity.repositories.passkey.passkey import (
    PasskeyCredentialRepository,
)
from com.qode.qrew.v1.identity.schemas.auth.auth import LoginResponse
from com.qode.qrew.v1.identity.schemas.passkey.passkey import (
    PasskeyAuthenticationCompleteRequest,
)
from com.qode.qrew.v1.identity.services.audit import AuditService
from com.qode.qrew.v1.identity.services.passkey._common import (
    CHALLENGE_TTL_SECONDS,
    PasskeyError,
    assertion_error_message,
    auth_challenge_key,
    build_assertion_credential,
    build_authentication_options,
    verify_assertion_response,
)

logger = structlog.get_logger(__name__)


class PasskeyAuthenticationService:
    """Sign a user in by verifying a passkey assertion."""

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

    async def begin(self, email: str) -> str:
        """Generate assertion options and cache the challenge."""
        user = await self._user_repo.get_by_email(email)
        if user is None or not user.is_active or not user.email_verified:
            raise PasskeyError("No passkey found for this account")

        credentials = await self._passkey_repo.get_all_by_user_id(user.id)
        if not credentials:
            raise PasskeyError("No passkey registered for this account")

        options = build_authentication_options(credentials)
        await self._redis.set(
            auth_challenge_key(user.id),
            options.challenge,
            ex=CHALLENGE_TTL_SECONDS,
        )
        await logger.ainfo("passkey_authentication_begin", user_id=str(user.id))
        return webauthn.options_to_json(options)

    async def complete(
        self,
        request: PasskeyAuthenticationCompleteRequest,
        ip_address: str | None = None,
        user_agent: str | None = None,
        device_fingerprint: str | None = None,
    ) -> LoginResponse:
        """Verify the assertion and return access tokens."""
        stored = await self._lookup_credential(request)
        user = await self._lookup_user(stored.user_id)
        raw_challenge = await self._consume_challenge(user.id)
        verification = self._verify(user, request, raw_challenge, stored)

        stored.sign_count = verification.new_sign_count
        stored.last_used_at = datetime.now(UTC)
        await self._passkey_repo.save(stored)

        return await self._issue_response(user, ip_address, user_agent, device_fingerprint)

    async def _lookup_credential(
        self, request: PasskeyAuthenticationCompleteRequest
    ) -> PasskeyCredential:
        """Look up the stored credential referenced by the assertion."""
        raw_id = base64url_to_bytes(request.raw_id)
        stored = await self._passkey_repo.get_by_credential_id(raw_id)
        if stored is None:
            await logger.awarning("passkey_authentication_failed", reason="credential_not_found")
            raise PasskeyError("Passkey not recognised")
        return stored

    async def _lookup_user(self, user_id: uuid.UUID) -> User:
        """Resolve the user that owns the asserted credential."""
        user = await self._user_repo.get_by_id(user_id)
        if user is None or not user.is_active:
            await logger.awarning(
                "passkey_authentication_failed", reason="user_not_found_or_inactive"
            )
            raise PasskeyError("Authentication failed")
        return user

    async def _consume_challenge(self, user_id: uuid.UUID) -> bytes:
        """Pop and return the cached authentication challenge."""
        key = auth_challenge_key(user_id)
        raw_challenge: bytes | None = await self._redis.get(key)
        if raw_challenge is None:
            await logger.awarning(
                "passkey_authentication_failed",
                reason="challenge_expired",
                user_id=str(user_id),
            )
            raise PasskeyError("Authentication session expired. Please start again.")
        await self._redis.delete(key)
        return raw_challenge

    def _verify(
        self,
        user: User,
        request: PasskeyAuthenticationCompleteRequest,
        raw_challenge: bytes,
        stored: PasskeyCredential,
    ) -> VerifiedAuthentication:
        """Run the WebAuthn verification or raise on failure."""
        credential = build_assertion_credential(request)
        try:
            return verify_assertion_response(credential, raw_challenge, stored)
        except Exception as exc:
            raise PasskeyError(assertion_error_message(exc, "authentication")) from exc

    async def _issue_response(
        self,
        user: User,
        ip_address: str | None,
        user_agent: str | None,
        device_fingerprint: str | None,
    ) -> LoginResponse:
        """Returns the appropriate token response depending on whether onboarding is complete."""
        setup_complete = user.phone_number_verified and user.kyc_status != KycStatus.not_submitted
        if setup_complete:
            refresh_token = create_refresh_token(str(user.id))
            session_jti = extract_jti(refresh_token)
            access_token = create_access_token(str(user.id), session_jti=session_jti)
            await self._persist_session(
                user.id, refresh_token, ip_address, user_agent, device_fingerprint
            )
            await logger.ainfo("passkey_authenticated", user_id=str(user.id))
            await self._audit_safe(user.id, setup_complete=True)
            return LoginResponse(access_token=access_token, refresh_token=refresh_token)

        await logger.ainfo("passkey_authenticated_setup_required", user_id=str(user.id))
        await self._audit_safe(user.id, setup_complete=False)
        return LoginResponse(access_token=create_setup_token(str(user.id)), setup_required=True)

    async def _persist_session(
        self,
        user_id: uuid.UUID,
        refresh_token: str,
        ip_address: str | None,
        user_agent: str | None,
        device_fingerprint: str | None,
    ) -> None:
        """Persist a new session row when full authentication succeeds."""
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

    async def _audit_safe(self, user_id: uuid.UUID, *, setup_complete: bool) -> None:
        """Record the authentication audit event without propagating errors."""
        try:
            await self._audit.record(
                action=AuditAction.PASSKEY_AUTHENTICATED,
                actor_id=user_id,
                entity_type="user",
                entity_id=str(user_id),
                payload={"setup_complete": setup_complete},
            )
        except Exception as exc:
            await logger.awarning(
                "audit_write_failed", action=AuditAction.PASSKEY_AUTHENTICATED, error=repr(exc)
            )
