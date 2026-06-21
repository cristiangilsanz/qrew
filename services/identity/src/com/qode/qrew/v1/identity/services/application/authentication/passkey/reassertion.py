from datetime import UTC, datetime

import redis.asyncio as aioredis
import structlog
import webauthn
from webauthn.helpers.base64url_to_bytes import base64url_to_bytes

from com.qode.qrew.v1.identity.models.audit import AuditAction
from com.qode.qrew.v1.identity.models.session import Session
from com.qode.qrew.v1.identity.models.user import User
from com.qode.qrew.v1.identity.repositories.session import SessionRepository
from com.qode.qrew.v1.identity.repositories.passkey import (
    PasskeyCredentialRepository,
)
from com.qode.qrew.v1.identity.schemas.passkey import (
    PasskeyAuthenticationCompleteRequest,
)
from com.qode.qrew.v1.identity.services.application.audit import AuditService
from com.qode.qrew.v1.identity.services.application.authentication.passkey.assertion import (
    ASSERT_CHALLENGE_TTL_SECONDS,
    PasskeyError,
    assert_challenge_key,
    assertion_error_message,
    build_assertion_credential,
    build_authentication_options,
    verify_assertion_response,
)

logger = structlog.get_logger(__name__)


class PasskeyReassertionService:
    """Verify a fresh passkey assertion for an already-authenticated session."""

    def __init__(
        self,
        passkey_repo: PasskeyCredentialRepository,
        redis: aioredis.Redis,  # type: ignore[type-arg]
        audit: AuditService,
        session_repo: SessionRepository | None = None,
    ) -> None:
        self._passkey_repo = passkey_repo
        self._redis = redis
        self._audit = audit
        self._session_repo = session_repo

    async def begin(self, user: User, session_jti: str) -> str:
        """Generate a short-lived assertion challenge bound to the session."""
        credentials = await self._passkey_repo.get_all_by_user_id(user.id)
        if not credentials:
            raise PasskeyError("No passkey registered for this account")
        options = build_authentication_options(credentials)
        await self._redis.set(
            assert_challenge_key(session_jti),
            options.challenge,
            ex=ASSERT_CHALLENGE_TTL_SECONDS,
        )
        await logger.ainfo("passkey_reassertion_begin", user_id=str(user.id))
        return webauthn.options_to_json(options)

    async def complete(
        self,
        user: User,
        session: Session,
        request: PasskeyAuthenticationCompleteRequest,
    ) -> datetime:
        """Verify a re-assertion and stamp the session timestamp."""
        raw_id = base64url_to_bytes(request.raw_id)
        stored = await self._passkey_repo.get_by_credential_id(raw_id)
        if stored is None or stored.user_id != user.id:
            raise PasskeyError("Passkey not recognised")

        raw_challenge = await self._consume_challenge(session.jti)
        credential = build_assertion_credential(request)
        try:
            verification = verify_assertion_response(credential, raw_challenge, stored)
        except Exception as exc:
            await logger.awarning(
                "passkey_reassertion_failed",
                reason="verification_failed",
                user_id=str(user.id),
                error=repr(exc),
            )
            raise PasskeyError(assertion_error_message(exc, "re-assertion")) from exc

        stored.sign_count = verification.new_sign_count
        stored.last_used_at = datetime.now(UTC)
        await self._passkey_repo.save(stored)

        asserted_at = datetime.now(UTC)
        if self._session_repo is not None:
            await self._session_repo.update_last_asserted_at(session.jti, asserted_at)

        await logger.ainfo("passkey_reasserted", user_id=str(user.id))
        await self._audit_safe(user, session)
        return asserted_at

    async def _consume_challenge(self, session_jti: str) -> bytes:
        """Pop and return the cached re-assertion challenge."""
        key = assert_challenge_key(session_jti)
        raw_challenge: bytes | None = await self._redis.get(key)
        if raw_challenge is None:
            raise PasskeyError("Re-assertion challenge expired. Please start again.")
        await self._redis.delete(key)
        return raw_challenge

    async def _audit_safe(self, user: User, session: Session) -> None:
        """Record the re-assertion audit event without propagating errors."""
        try:
            await self._audit.record(
                action=AuditAction.PASSKEY_REASSERTED,
                actor_id=user.id,
                entity_type="session",
                entity_id=str(session.id),
            )
        except Exception as exc:
            await logger.awarning(
                "audit_write_failed", action=AuditAction.PASSKEY_REASSERTED, error=repr(exc)
            )
