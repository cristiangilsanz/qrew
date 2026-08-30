# authenticates a user with a passkey and issues a session or setup token
import uuid
from datetime import UTC, datetime

import redis.asyncio as aioredis
import structlog
import webauthn
from webauthn.authentication.verify_authentication_response import (
    VerifiedAuthentication,
)
from webauthn.helpers.base64url_to_bytes import base64url_to_bytes

from com.qode.qrew.v1.identity.services.application.authentication.token.security import (
    create_access_token,
    create_refresh_token,
    create_setup_token,
    extract_jti,
)
from com.qode.qrew.v1.identity.models.audit import AuditAction
from com.qode.qrew.v1.identity.models.session import Session
from com.qode.qrew.v1.identity.models.user import KycStatus, User
from com.qode.qrew.v1.identity.models.passkey import PasskeyCredential
from com.qode.qrew.v1.identity.repositories.session import SessionRepository
from com.qode.qrew.v1.identity.repositories.user import UserRepository
from com.qode.qrew.v1.identity.repositories.passkey import (
    PasskeyCredentialRepository,
)
from com.qode.qrew.v1.identity.schemas.authentication.auth import LoginResponse
from com.qode.qrew.v1.identity.schemas.passkey import (
    PasskeyAuthenticationCompleteRequest,
)
from com.qode.qrew.v1.identity.services.application.audit import AuditService
from com.qode.qrew.v1.identity.services.application.authentication.passkey.assertion import (
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
    # stores the repositories redis client and audit service the service uses
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

    # generates the webauthn options for the account's registered passkeys
    async def begin(self, email: str) -> str:
        user = await self._user_repo.get_by_email(email)
        if user is None or not user.is_active or not user.email_verified:
            raise PasskeyError("Passkey not found.")

        credentials = await self._passkey_repo.get_all_by_user_id(user.id)
        if not credentials:
            raise PasskeyError("Passkey not registered.")

        options = build_authentication_options(credentials)
        await self._redis.set(
            auth_challenge_key(user.id),
            options.challenge,
            ex=CHALLENGE_TTL_SECONDS,
        )
        await logger.ainfo("passkey_authentication_begin", user_id=str(user.id))
        return webauthn.options_to_json(options)

    # verifies the assertion and issues whichever token the account's state calls for
    async def complete(
        self,
        request: PasskeyAuthenticationCompleteRequest,
        ip_address: str | None = None,
        user_agent: str | None = None,
        device_fingerprint: str | None = None,
    ) -> LoginResponse:
        stored = await self._lookup_credential(request)
        user = await self._lookup_user(stored.user_id)
        raw_challenge = await self._consume_challenge(user.id)
        verification = self._verify(user, request, raw_challenge, stored)

        stored.sign_count = verification.new_sign_count
        stored.last_used_at = datetime.now(UTC)
        await self._passkey_repo.save(stored)

        return await self._issue_response(user, ip_address, user_agent, device_fingerprint)

    # resolves the stored credential the assertion claims to be
    async def _lookup_credential(
        self, request: PasskeyAuthenticationCompleteRequest
    ) -> PasskeyCredential:
        raw_id = base64url_to_bytes(request.raw_id)
        stored = await self._passkey_repo.get_by_credential_id(raw_id)
        if stored is None:
            await logger.awarning("passkey_authentication_failed", reason="credential_not_found")
            raise PasskeyError("Passkey rejected.")
        return stored

    # resolves the active user a credential belongs to
    async def _lookup_user(self, user_id: uuid.UUID) -> User:
        user = await self._user_repo.get_by_id(user_id)
        if user is None or not user.is_active:
            await logger.awarning(
                "passkey_authentication_failed", reason="user_not_found_or_inactive"
            )
            raise PasskeyError("Authentication failed.")
        return user

    # reads and deletes the pending authentication challenge
    async def _consume_challenge(self, user_id: uuid.UUID) -> bytes:
        key = auth_challenge_key(user_id)
        raw_challenge: bytes | None = await self._redis.get(key)
        if raw_challenge is None:
            await logger.awarning(
                "passkey_authentication_failed",
                reason="challenge_expired",
                user_id=str(user_id),
            )
            raise PasskeyError("Authentication session expired.")
        await self._redis.delete(key)
        return raw_challenge

    # verifies the webauthn assertion against the stored credential
    def _verify(
        self,
        user: User,
        request: PasskeyAuthenticationCompleteRequest,
        raw_challenge: bytes,
        stored: PasskeyCredential,
    ) -> VerifiedAuthentication:
        try:
            credential = build_assertion_credential(request)
            return verify_assertion_response(credential, raw_challenge, stored)
        except Exception as exc:
            raise PasskeyError(assertion_error_message(exc, "authentication")) from exc

    # issues a full session or a setup token depending on onboarding state
    async def _issue_response(
        self,
        user: User,
        ip_address: str | None,
        user_agent: str | None,
        device_fingerprint: str | None,
    ) -> LoginResponse:
        setup_complete = user.phone_number_verified and user.kyc_status != KycStatus.not_submitted
        if setup_complete:
            refresh_token = create_refresh_token(str(user.id))
            session_jti = extract_jti(refresh_token)
            access_token = create_access_token(
                str(user.id), session_jti=session_jti, is_admin=user.is_admin
            )
            await self._persist_session(
                user.id, refresh_token, ip_address, user_agent, device_fingerprint
            )
            await logger.ainfo("passkey_authenticated", user_id=str(user.id))
            await self._audit_safe(user.id, setup_complete=True)
            return LoginResponse(access_token=access_token, refresh_token=refresh_token)

        await logger.ainfo("passkey_authenticated_setup_required", user_id=str(user.id))
        await self._audit_safe(user.id, setup_complete=False)
        return LoginResponse(access_token=create_setup_token(str(user.id)), setup_required=True)

    # writes the new session tied to its refresh token
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

    # records the passkey authentication without letting a failure interrupt it
    async def _audit_safe(self, user_id: uuid.UUID, *, setup_complete: bool) -> None:
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
