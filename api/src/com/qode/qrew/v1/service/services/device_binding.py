import base64
import uuid
from datetime import UTC, datetime

import redis.asyncio as aioredis
import structlog
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ec import ECDSA, EllipticCurvePublicKey
from cryptography.hazmat.primitives.asymmetric.utils import encode_dss_signature
from cryptography.hazmat.primitives.hashes import SHA256
from cryptography.hazmat.primitives.serialization import load_der_public_key

from com.qode.qrew.v1.service.core.errors import DomainError
from com.qode.qrew.v1.service.models.audit import AuditAction
from com.qode.qrew.v1.service.models.device import Device
from com.qode.qrew.v1.service.models.user import User
from com.qode.qrew.v1.service.repositories.device import DeviceRepository
from com.qode.qrew.v1.service.services.audit import AuditService
from com.qode.qrew.v1.service.services.device_attestation import consume_attestation
from com.qode.qrew.v1.service.settings import settings

logger = structlog.get_logger(__name__)

_CHALLENGE_PREFIX = "device:bind:challenge:"
_CHALLENGE_TTL_SECONDS = 300


class DeviceBindingError(DomainError):
    """Raised when a device binding operation cannot be completed."""


class DeviceBindingService:
    def __init__(
        self,
        device_repo: DeviceRepository,
        redis: aioredis.Redis,  # type: ignore[type-arg]
        audit: AuditService,
    ) -> None:
        self._device_repo = device_repo
        self._redis = redis
        self._audit = audit

    async def begin(self, user: User) -> str:
        """Generate a challenge nonce and store it in Redis. Returns the challenge."""
        challenge = str(uuid.uuid4())
        await self._redis.set(
            _CHALLENGE_PREFIX + str(user.id),
            challenge,
            ex=_CHALLENGE_TTL_SECONDS,
        )
        await logger.ainfo("device_bind_begin", user_id=str(user.id))
        return challenge

    async def complete(
        self,
        user: User,
        name: str,
        public_key_b64: str,
        signature_b64: str,
    ) -> Device:
        """Verify ECDSA signature over the challenge, persist the device."""
        raw_challenge: bytes | None = await self._redis.get(
            _CHALLENGE_PREFIX + str(user.id)
        )
        if raw_challenge is None:
            raise DeviceBindingError(
                "Binding session expired. Please start again.", field=None
            )
        await self._redis.delete(_CHALLENGE_PREFIX + str(user.id))

        challenge_str = raw_challenge.decode()

        try:
            public_key_bytes = base64.urlsafe_b64decode(_pad_b64(public_key_b64))
        except Exception as exc:
            raise DeviceBindingError(
                "Invalid public key encoding.", field="public_key"
            ) from exc

        try:
            pub_key = load_der_public_key(public_key_bytes)
        except Exception as exc:
            raise DeviceBindingError(
                "Invalid public key format. Expected SPKI DER.", field="public_key"
            ) from exc

        if not isinstance(pub_key, EllipticCurvePublicKey):
            raise DeviceBindingError(
                "Only ECDSA P-256 keys are accepted.", field="public_key"
            )

        try:
            sig_bytes = base64.urlsafe_b64decode(_pad_b64(signature_b64))
        except Exception as exc:
            raise DeviceBindingError(
                "Invalid signature encoding.", field="signature"
            ) from exc

        verify_ecdsa(pub_key, sig_bytes, challenge_str.encode())

        existing = await self._device_repo.get_by_public_key(public_key_bytes)
        if existing is not None:
            raise DeviceBindingError(
                "This key is already registered.", field="public_key"
            )

        platform = await consume_attestation(self._redis, user.id)
        if settings.attestation_enabled and platform is None:
            raise DeviceBindingError(
                "Device attestation required before binding.",
                field=None,
            )

        now = datetime.now(UTC)
        device = await self._device_repo.create(
            Device(
                id=uuid.uuid4(),
                user_id=user.id,
                name=name,
                public_key=public_key_bytes,
                last_seen_at=now,
                attested_at=now if platform and platform != "skipped" else None,
                attestation_platform=platform
                if platform and platform != "skipped"
                else None,
            )
        )

        await logger.ainfo("device_bind_complete", user_id=str(user.id))
        try:
            await self._audit.record(
                action=AuditAction.DEVICE_BIND,
                actor_id=user.id,
                entity_type="device",
                entity_id=str(device.id),
                payload={"device_name": name},
            )
        except Exception:
            await logger.awarning("audit_write_failed", action=AuditAction.DEVICE_BIND)

        return device


def _pad_b64(value: str) -> str:
    """Add base64url padding if missing."""
    return value + "=" * (-len(value) % 4)


def verify_ecdsa(
    pub_key: EllipticCurvePublicKey,
    sig_bytes: bytes,
    data: bytes,
) -> None:
    """Verify ECDSA-P256-SHA256. Accepts DER or raw P1363 (r||s) signatures."""
    key_size_bytes = (pub_key.key_size + 7) // 8
    p1363_len = key_size_bytes * 2

    if len(sig_bytes) == p1363_len:
        r = int.from_bytes(sig_bytes[:key_size_bytes], "big")
        s = int.from_bytes(sig_bytes[key_size_bytes:], "big")
        der_sig = encode_dss_signature(r, s)
    else:
        der_sig = sig_bytes

    try:
        pub_key.verify(der_sig, data, ECDSA(SHA256()))
    except InvalidSignature as exc:
        raise DeviceBindingError(
            "Signature verification failed.", field="signature"
        ) from exc
    except Exception as exc:
        raise DeviceBindingError(
            "Signature verification failed.", field="signature"
        ) from exc
