from dataclasses import dataclass

from com.qode.qrew.v1.identity.services.storage.backend import StorageBackend
from com.qode.qrew.v1.identity.services.storage.encryption import (
    decrypt as _decrypt,
)
from com.qode.qrew.v1.identity.services.storage.encryption import (
    encrypt as _encrypt,
)
from com.qode.qrew.v1.identity.services.storage.encryption import (
    should_encrypt,
)
from com.qode.qrew.v1.identity.services.storage.keys import (
    ObjectKey,
    build_key,
    is_known_kind,
    kind_for,
)
from com.qode.qrew.v1.identity.services.storage.signing import SignedUrl


@dataclass(frozen=True)
class UploadConstraint:
    max_size_bytes: int
    allowed_content_types: frozenset[str]


_CONSTRAINTS: dict[str, UploadConstraint] = {
    "kyc": UploadConstraint(
        max_size_bytes=10 * 1024 * 1024,
        allowed_content_types=frozenset({"image/jpeg", "image/png", "application/pdf"}),
    ),
    "event_image": UploadConstraint(
        max_size_bytes=5 * 1024 * 1024,
        allowed_content_types=frozenset({"image/jpeg", "image/png", "image/webp"}),
    ),
    "scanner_photo": UploadConstraint(
        max_size_bytes=5 * 1024 * 1024,
        allowed_content_types=frozenset({"image/jpeg", "image/png"}),
    ),
}


def constraint_for(kind: str) -> UploadConstraint:
    """Return the upload limits configured for a given object category."""
    if kind not in _CONSTRAINTS:
        raise ValueError(f"unknown kind: {kind}")
    return _CONSTRAINTS[kind]


class StorageService:
    """High-level facade for storing, retrieving, and signing storage objects."""

    def __init__(self, backend: StorageBackend) -> None:
        self._backend = backend

    async def put(
        self,
        *,
        kind: str,
        tenant: str,
        content: bytes,
        content_type: str,
    ) -> ObjectKey:
        """Persist a new object and return its key."""
        if not is_known_kind(kind):
            raise ValueError(f"unknown kind: {kind}")
        key = build_key(tenant=tenant, kind=kind)
        body = _encrypt(content) if should_encrypt(kind) else content
        await self._backend.put(key, body, content_type)
        return key

    async def get(self, key: ObjectKey) -> bytes:
        """Read and decrypt an object, transparent to the caller."""
        raw = await self._backend.get(key)
        return _decrypt(raw) if should_encrypt(kind_for(key)) else raw

    async def delete(self, key: ObjectKey) -> None:
        """Delete an object if it exists."""
        await self._backend.delete(key)

    async def exists(self, key: ObjectKey) -> bool:
        return await self._backend.exists(key)

    def sign_put_url(
        self,
        *,
        kind: str,
        tenant: str,
        content_type: str,
        ttl_seconds: int,
    ) -> SignedUrl:
        """Mint a short-lived signed PUT URL for a new object."""
        constraint = constraint_for(kind)
        if content_type not in constraint.allowed_content_types:
            raise ValueError(f"content_type not allowed for {kind}")
        key = build_key(tenant=tenant, kind=kind)
        return self._backend.sign_put_url(key, content_type, ttl_seconds)

    def sign_get_url(self, key: ObjectKey, ttl_seconds: int) -> SignedUrl:
        """Mint a short-lived signed GET URL for an existing object."""
        return self._backend.sign_get_url(key, ttl_seconds)

    async def verify_signed_put(
        self,
        key: ObjectKey,
        content_type: str,
        expires_at: int,
        signature: str,
    ) -> None:
        """Validate a signed PUT request, raising on tamper or expiry."""
        await self._backend.verify_signed_put(key, content_type, expires_at, signature)

    async def verify_signed_get(self, key: ObjectKey, expires_at: int, signature: str) -> None:
        """Validate a signed GET request, raising on tamper or expiry."""
        await self._backend.verify_signed_get(key, expires_at, signature)
