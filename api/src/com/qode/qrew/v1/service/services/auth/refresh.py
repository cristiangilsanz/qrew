import base64
import uuid
from datetime import UTC, datetime

import redis.asyncio as aioredis
import structlog
from cryptography.hazmat.primitives.asymmetric.ec import EllipticCurvePublicKey
from cryptography.hazmat.primitives.serialization import load_der_public_key
from jwt import ExpiredSignatureError, InvalidTokenError

from com.qode.qrew.v1.service.core.auth import jwt_keys
from com.qode.qrew.v1.service.core.auth.security import (
    create_access_token,
    create_refresh_token,
    extract_jti,
)
from com.qode.qrew.v1.service.core.infra.errors import DomainError
from com.qode.qrew.v1.service.models.audit.audit import AuditAction
from com.qode.qrew.v1.service.repositories.auth.session import SessionRepository
from com.qode.qrew.v1.service.repositories.auth.user import UserRepository
from com.qode.qrew.v1.service.repositories.device.device import DeviceRepository
from com.qode.qrew.v1.service.schemas.auth.auth import (
    RefreshRequest,
    RefreshResponse,
)
from com.qode.qrew.v1.service.services.audit import AuditService
from com.qode.qrew.v1.service.services.auth.logout import (
    BLACKLIST_JTI_PREFIX,
    BLACKLIST_USER_PREFIX,
)
from com.qode.qrew.v1.service.services.device.device_binding import (
    DeviceBindingError,
    verify_ecdsa,
)
from com.qode.qrew.v1.service.settings import settings

logger = structlog.get_logger(__name__)

_ROTATED = b"rotated"


def signature_payload(jti: str, iat: int) -> bytes:
    """Return the bytes the client must sign for a device-bound refresh."""
    return f"{jti}|{iat}".encode()


def decode_signature_header(raw: str | None) -> bytes | None:
    """Decode a base64url device signature header."""
    if raw is None:
        return None
    padded = raw + "=" * (-len(raw) % 4)
    try:
        return base64.urlsafe_b64decode(padded)
    except Exception:
        return None


class RefreshError(DomainError):
    """A business-rule violation raised when a token refresh cannot be completed."""


class RefreshService:
    def __init__(
        self,
        repo: UserRepository,
        redis: aioredis.Redis,  # type: ignore[type-arg]
        audit: AuditService,
        session_repo: SessionRepository | None = None,
        device_repo: DeviceRepository | None = None,
    ) -> None:
        self._repo = repo
        self._redis = redis
        self._audit = audit
        self._session_repo = session_repo
        self._device_repo = device_repo

    async def refresh(
        self,
        request: RefreshRequest,
        device_signature: bytes | None = None,
    ) -> RefreshResponse:
        """Issue a new access + refresh token pair, invalidating the old one."""
        try:
            payload = jwt_keys.verify(jwt_keys.REFRESH, request.refresh_token)
        except ExpiredSignatureError as exc:
            await logger.awarning("refresh_failed", reason="token_expired")
            raise RefreshError("Refresh token has expired") from exc
        except InvalidTokenError as exc:
            await logger.awarning("refresh_failed", reason="invalid_token")
            raise RefreshError("Invalid refresh token") from exc

        if payload.get("type") != "refresh":
            await logger.awarning("refresh_failed", reason="wrong_token_type")
            raise RefreshError("Invalid token type")

        jti = payload.get("jti")
        subject = payload.get("sub")
        jti_key = BLACKLIST_JTI_PREFIX + jti if isinstance(jti, str) else None

        if jti_key:
            await self._check_jti(jti_key, subject, jti)

        if not isinstance(subject, str):
            await logger.awarning("refresh_failed", reason="invalid_subject")
            raise RefreshError("Invalid refresh token")

        await self._check_user_revocation(subject, payload.get("iat"))

        try:
            user_id = uuid.UUID(subject)
        except ValueError as exc:
            await logger.awarning("refresh_failed", reason="invalid_subject")
            raise RefreshError("Invalid refresh token") from exc

        user = await self._repo.get_by_id(user_id)
        if user is None or not user.is_active:
            await logger.awarning("refresh_failed", reason="user_not_found_or_inactive")
            raise RefreshError("Invalid refresh token")

        bound_device_id = await self.check_device_binding(
            jti, payload.get("iat"), device_signature, user_id
        )

        if jti_key:
            await self._rotate_jti(jti_key, payload.get("exp"))

        new_refresh_token = create_refresh_token(str(user.id))
        new_jti = extract_jti(new_refresh_token)
        access_token = create_access_token(
            str(user.id),
            device_id=str(bound_device_id) if bound_device_id else None,
            session_jti=new_jti,
        )

        if (
            self._session_repo is not None
            and isinstance(jti, str)
            and new_jti is not None
        ):
            await self._session_repo.update_jti(jti, new_jti)

        await logger.ainfo("token_refreshed", user_id=str(user.id))
        try:
            await self._audit.record(
                action=AuditAction.TOKEN_REFRESHED,
                actor_id=user.id,
                entity_type="user",
                entity_id=str(user.id),
            )
        except Exception:
            await logger.awarning(
                "audit_write_failed", action=AuditAction.TOKEN_REFRESHED
            )

        return RefreshResponse(
            access_token=access_token,
            refresh_token=new_refresh_token,
        )

    async def _check_jti(self, jti_key: str, subject: object, jti: object) -> None:
        """Raise if the JTI is blacklisted; trigger theft detection on replay."""
        stored: bytes | None = await self._redis.get(jti_key)
        if stored is None:
            return
        if stored == _ROTATED and isinstance(subject, str) and isinstance(jti, str):
            await self._handle_theft(subject, jti)
        await logger.awarning("refresh_failed", reason="token_revoked")
        raise RefreshError("Refresh token has been revoked")

    async def _handle_theft(self, subject: str, jti: str) -> None:
        """Revoke all tokens for the user and record the theft event."""
        ttl = settings.refresh_token_expire_days * 24 * 3600
        await self._redis.setex(
            BLACKLIST_USER_PREFIX + subject,
            ttl,
            str(int(datetime.now(UTC).timestamp())),
        )
        if self._session_repo is not None:
            try:
                user_id = uuid.UUID(subject)
                await self._session_repo.delete_all_by_user_id(user_id)
            except ValueError:
                pass
        await logger.awarning("refresh_theft_detected", user_id=subject, jti=jti)
        try:
            actor_id = uuid.UUID(subject)
            await self._audit.record(
                action=AuditAction.TOKEN_THEFT_DETECTED,
                actor_id=actor_id,
                entity_type="user",
                entity_id=subject,
                payload={"jti": jti},
            )
        except Exception:
            await logger.awarning(
                "audit_write_failed", action=AuditAction.TOKEN_THEFT_DETECTED
            )

    async def _check_user_revocation(self, subject: str, iat: object) -> None:
        """Raise if a user-level revocation covers this token's issue time."""
        revoked_at_raw: bytes | None = await self._redis.get(
            BLACKLIST_USER_PREFIX + subject
        )
        if (
            revoked_at_raw is not None
            and isinstance(iat, (int, float))
            and int(iat) <= int(revoked_at_raw)
        ):
            await logger.awarning("refresh_failed", reason="all_tokens_revoked")
            raise RefreshError("Refresh token has been revoked")

    async def check_device_binding(
        self,
        jti: object,
        iat: object,
        signature: bytes | None,
        actor_id: uuid.UUID,
    ) -> uuid.UUID | None:
        """If the session is device-bound, verify the ECDSA signature over jti||iat."""
        if self._session_repo is None or not isinstance(jti, str):
            return None
        session = await self._session_repo.get_by_jti(jti)
        if session is None or session.device_id is None:
            return None
        if not isinstance(iat, (int, float)):
            raise RefreshError("Invalid refresh token")

        if signature is None:
            await self._audit_signature_failure(actor_id, jti, "missing_signature")
            await logger.awarning(
                "refresh_failed", reason="missing_device_signature", jti=jti
            )
            raise RefreshError("Refresh requires a device signature")

        if self._device_repo is None:
            return session.device_id
        device = await self._device_repo.get_by_id(session.device_id)
        if device is None or device.revoked_at is not None:
            await self._audit_signature_failure(actor_id, jti, "device_missing")
            raise RefreshError("Bound device is no longer valid")

        signed_payload = signature_payload(jti, int(iat))
        try:
            pub_key = load_der_public_key(device.public_key)
        except Exception as exc:
            await self._audit_signature_failure(actor_id, jti, "bad_public_key")
            raise RefreshError("Invalid bound device public key") from exc
        if not isinstance(pub_key, EllipticCurvePublicKey):
            await self._audit_signature_failure(actor_id, jti, "bad_public_key")
            raise RefreshError("Invalid bound device public key")

        try:
            verify_ecdsa(pub_key, signature, signed_payload)
        except DeviceBindingError as exc:
            await self._audit_signature_failure(actor_id, jti, "bad_signature")
            await logger.awarning(
                "refresh_failed", reason="device_signature_invalid", jti=jti
            )
            raise RefreshError("Refresh device signature invalid") from exc
        return session.device_id

    async def _audit_signature_failure(
        self, actor_id: uuid.UUID, jti: str, reason: str
    ) -> None:
        try:
            await self._audit.record(
                action=AuditAction.REFRESH_SIGNATURE_INVALID,
                actor_id=actor_id,
                entity_type="user",
                entity_id=str(actor_id),
                payload={"jti": jti, "reason": reason},
            )
        except Exception:
            await logger.awarning(
                "audit_write_failed",
                action=AuditAction.REFRESH_SIGNATURE_INVALID,
            )

    async def _rotate_jti(self, jti_key: str, exp: object) -> None:
        """Blacklist the old JTI as rotated so any replay triggers theft detection."""
        ttl = (
            int(exp) - int(datetime.now(UTC).timestamp())
            if isinstance(exp, (int, float))
            else 0
        )
        if ttl > 0:
            await self._redis.setex(jti_key, ttl, "rotated")
