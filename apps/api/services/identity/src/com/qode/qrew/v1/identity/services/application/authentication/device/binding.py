# binds a device to a user by verifying its ecdsa challenge response
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

from sqlalchemy.ext.asyncio import AsyncSession

from outbox import record as record_event

from com.qode.qrew.v1.identity.models.event_outbox import EventOutbox
from com.qode.qrew.v1.identity.core.errors import DomainError
from com.qode.qrew.v1.identity.models.audit import AuditAction
from com.qode.qrew.v1.identity.models.user import User
from com.qode.qrew.v1.identity.models.device import Device
from com.qode.qrew.v1.identity.repositories.device import DeviceRepository
from com.qode.qrew.v1.identity.services.application.audit import AuditService
from com.qode.qrew.v1.identity.services.application.authentication.device.attestation.attestor import (
    consume_attestation,
)
from com.qode.qrew.v1.identity.core.config import settings

logger = structlog.get_logger(__name__)

_CHALLENGE_PREFIX = "device:bind:challenge:"
_CHALLENGE_TTL_SECONDS = 300


class DeviceBindingError(DomainError):
    pass


class DeviceBindingService:
    # stores the repository redis client and audit service the service uses
    def __init__(
        self,
        device_repo: DeviceRepository,
        redis: aioredis.Redis,  # type: ignore[type-arg]
        audit: AuditService,
    ) -> None:
        self._device_repo = device_repo
        self._redis = redis
        self._audit = audit

    # generates a short lived challenge for the device to sign
    async def begin(self, user: User) -> str:
        challenge = str(uuid.uuid4())
        await self._redis.set(
            _CHALLENGE_PREFIX + str(user.id),
            challenge,
            ex=_CHALLENGE_TTL_SECONDS,
        )
        await logger.ainfo("device_bind_begin", user_id=str(user.id))
        return challenge

    # verifies the signed challenge and registers the device
    async def complete(
        self,
        user: User,
        name: str,
        public_key_b64: str,
        signature_b64: str,
    ) -> Device:
        raw_challenge: bytes | None = await self._redis.get(_CHALLENGE_PREFIX + str(user.id))
        if raw_challenge is None:
            raise DeviceBindingError("Binding session expired.", field=None)
        await self._redis.delete(_CHALLENGE_PREFIX + str(user.id))

        challenge_str = raw_challenge.decode()

        try:
            public_key_bytes = base64.urlsafe_b64decode(_pad_b64(public_key_b64))
        except Exception as exc:
            raise DeviceBindingError("Device key rejected.", field="public_key") from exc

        try:
            pub_key = load_der_public_key(public_key_bytes)
        except Exception as exc:
            raise DeviceBindingError(
                "Invalid public key format. Expected SPKI DER.", field="public_key"
            ) from exc

        if not isinstance(pub_key, EllipticCurvePublicKey):
            raise DeviceBindingError("Device key rejected.", field="public_key")

        try:
            sig_bytes = base64.urlsafe_b64decode(_pad_b64(signature_b64))
        except Exception as exc:
            raise DeviceBindingError("Signature rejected.", field="signature") from exc

        verify_ecdsa(pub_key, sig_bytes, challenge_str.encode())

        existing = await self._device_repo.get_by_public_key(public_key_bytes)
        if existing is not None and existing.user_id != user.id:
            raise DeviceBindingError("Device key already registered.", field="public_key")
        if existing is not None and existing.revoked_at is None:
            raise DeviceBindingError("Device key already registered.", field="public_key")

        platform = await consume_attestation(self._redis, user.id)
        if settings.attestation_enabled and platform is None:
            raise DeviceBindingError(
                "Device attestation required before binding.",
                field=None,
            )

        now = datetime.now(UTC)
        # a device key lives in the browser and never changes, so revoking one and
        # binding it again arrives with the same key. refusing that would lock the
        # holder out of their own device for good, and the holder is authenticated
        # and has just signed the challenge, so the binding is revived instead.
        if existing is not None:
            existing.revoked_at = None
            existing.name = name
            existing.last_seen_at = now
            existing.attested_at = now if platform and platform != "skipped" else None
            existing.attestation_platform = platform if platform and platform != "skipped" else None
            device = await self._device_repo.save(existing)
            await logger.ainfo("device_bind_revived", user_id=str(user.id))
            await self._audit_safe(user.id, device.id, name)
            await _publish_device_attested(
                self._device_repo.session, device, platform=platform, attested_at=now
            )
            return device

        device = await self._device_repo.create(
            Device(
                id=uuid.uuid4(),
                user_id=user.id,
                name=name,
                public_key=public_key_bytes,
                last_seen_at=now,
                attested_at=now if platform and platform != "skipped" else None,
                attestation_platform=platform if platform and platform != "skipped" else None,
            )
        )

        await logger.ainfo("device_bind_complete", user_id=str(user.id))
        await self._audit_safe(user.id, device.id, name)
        await _publish_device_attested(
            self._device_repo.session, device, platform=platform, attested_at=now
        )

        return device

    # records the binding without letting an audit failure undo it
    async def _audit_safe(self, user_id: uuid.UUID, device_id: uuid.UUID, name: str) -> None:
        try:
            await self._audit.record(
                action=AuditAction.DEVICE_BIND,
                actor_id=user_id,
                entity_type="device",
                entity_id=str(device_id),
                payload={"device_name": name},
            )
        except Exception as exc:
            await logger.awarning(
                "audit_write_failed", action=AuditAction.DEVICE_BIND, error=repr(exc)
            )


# leaves in the outbox that a device was bound
async def _publish_device_attested(
    session: AsyncSession, device: Device, *, platform: str | None, attested_at: datetime
) -> None:
    await record_event(
        session,
        EventOutbox,
        subject="identity.device.attested.v1",
        aggregate_type="device",
        aggregate_id=str(device.id),
        actor_id=str(device.user_id),
        data={
            "device_id": str(device.id),
            "user_id": str(device.user_id),
            "attested_at": attested_at.isoformat(),
            "platform": platform,
        },
    )


# adds the padding a base64url string needs to decode
def _pad_b64(value: str) -> str:
    return value + "=" * (-len(value) % 4)


# verifies an ecdsa signature accepting either raw or der encoding
def verify_ecdsa(
    pub_key: EllipticCurvePublicKey,
    sig_bytes: bytes,
    data: bytes,
) -> None:
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
        raise DeviceBindingError("Signature rejected.", field="signature") from exc
    except Exception as exc:
        raise DeviceBindingError("Signature rejected.", field="signature") from exc
