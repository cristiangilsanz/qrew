import uuid

import redis.asyncio as aioredis
import structlog

from com.qode.qrew.v1.identity.services.device.attestation import (
    AttestationResult,
    AttestationVerifier,
    AttestationVerifierError,
)
from com.qode.qrew.v1.identity.core.errors import DomainError
from com.qode.qrew.v1.identity.models.audit.audit import AuditAction
from com.qode.qrew.v1.identity.services.audit import AuditService
from com.qode.qrew.v1.identity.core.config import settings

logger = structlog.get_logger(__name__)

_BIND_CHALLENGE_PREFIX = "device:bind:challenge:"
ATTESTED_PREFIX = "device:attested:"
_ATTESTED_TTL_SECONDS = 300


def attested_key(user_id: uuid.UUID) -> str:
    return f"{ATTESTED_PREFIX}{user_id}"


class DeviceAttestationError(DomainError):
    """Raised when a device attestation is rejected."""


class DeviceAttestationService:
    def __init__(
        self,
        verifier: AttestationVerifier,
        redis: aioredis.Redis,  # type: ignore[type-arg]
        audit: AuditService,
    ) -> None:
        self._verifier = verifier
        self._redis = redis
        self._audit = audit

    async def attest(
        self,
        user_id: uuid.UUID,
        platform: str,
        token: str,
    ) -> AttestationResult:
        """Verify the verdict against the active bind challenge for the user."""
        nonce_raw: bytes | None = await self._redis.get(_BIND_CHALLENGE_PREFIX + str(user_id))
        if nonce_raw is None:
            raise DeviceAttestationError(
                "No active bind challenge. Call bind/begin first.", field=None
            )
        nonce = nonce_raw.decode()

        try:
            if platform == "android":
                result = await self._verifier.verify_android(token, nonce)
            elif platform == "ios":
                result = await self._verifier.verify_ios(token, nonce)
            else:
                raise DeviceAttestationError("Unsupported platform.", field="platform")
        except AttestationVerifierError as exc:
            await logger.awarning(
                "device_attestation_failed",
                user_id=str(user_id),
                platform=platform,
                reason=str(exc),
            )
            try:
                await self._audit.record(
                    action=AuditAction.DEVICE_ATTESTATION_FAILED,
                    actor_id=user_id,
                    entity_type="user",
                    entity_id=str(user_id),
                    payload={"platform": platform, "reason": str(exc)},
                )
            except Exception:
                await logger.awarning(
                    "audit_write_failed",
                    action=AuditAction.DEVICE_ATTESTATION_FAILED,
                )
            raise DeviceAttestationError(str(exc), field=None) from exc

        await self._redis.setex(attested_key(user_id), _ATTESTED_TTL_SECONDS, result.platform)

        await logger.ainfo("device_attested", user_id=str(user_id), platform=result.platform)
        try:
            await self._audit.record(
                action=AuditAction.DEVICE_ATTESTED,
                actor_id=user_id,
                entity_type="user",
                entity_id=str(user_id),
                payload={"platform": result.platform},
            )
        except Exception:
            await logger.awarning("audit_write_failed", action=AuditAction.DEVICE_ATTESTED)
        return result


async def consume_attestation(
    redis: aioredis.Redis,  # type: ignore[type-arg]
    user_id: uuid.UUID,
) -> str | None:
    """Consume and return any pending attestation flag for the user."""
    if not settings.attestation_enabled:
        return "skipped"
    key = attested_key(user_id)
    raw: bytes | None = await redis.get(key)
    if raw is None:
        return None
    await redis.delete(key)
    return raw.decode()
