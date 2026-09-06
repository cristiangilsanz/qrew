# stores and serves upload objects encrypting the kinds that require it
from dataclasses import dataclass

from com.qode.qrew.v1.identity.services.application.storage.providers.protocol import StorageBackend
from com.qode.qrew.v1.identity.services.application.storage.security.encryption import (
    decrypt as _decrypt,
)
from com.qode.qrew.v1.identity.services.application.storage.security.encryption import (
    encrypt as _encrypt,
)
from com.qode.qrew.v1.identity.services.application.storage.security.encryption import (
    should_encrypt,
)
from com.qode.qrew.v1.identity.services.application.storage.security.keys import (
    ObjectKey,
    build_key,
    is_known_kind,
    kind_for,
)
from com.qode.qrew.v1.identity.services.application.storage.security.signing import SignedUrl


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
        allowed_content_types=frozenset(
            {"image/jpeg", "image/png", "image/webp", "image/heic", "image/heif"}
        ),
    ),
    "scanner_photo": UploadConstraint(
        max_size_bytes=5 * 1024 * 1024,
        allowed_content_types=frozenset({"image/jpeg", "image/png"}),
    ),
}


# looks up the size and content type limits for an upload kind
def constraint_for(kind: str) -> UploadConstraint:
    if kind not in _CONSTRAINTS:
        raise ValueError(f"unknown kind: {kind}")
    return _CONSTRAINTS[kind]


class StorageService:
    # stores the backend the service delegates to
    def __init__(self, backend: StorageBackend) -> None:
        self._backend = backend

    # writes a new object under a fresh key and encrypts it if required
    async def put(
        self,
        *,
        kind: str,
        tenant: str,
        content: bytes,
        content_type: str,
    ) -> ObjectKey:
        if not is_known_kind(kind):
            raise ValueError(f"unknown kind: {kind}")
        key = build_key(tenant=tenant, kind=kind)
        body = _encrypt(content) if should_encrypt(kind) else content
        await self._backend.put(key, body, content_type)
        return key

    # writes an object at an already assigned key and encrypts it if required
    async def store_at(self, key: ObjectKey, content: bytes, content_type: str) -> None:
        kind = kind_for(key)
        body = _encrypt(content) if should_encrypt(kind) else content
        await self._backend.put(key, body, content_type)

    # reads an object and decrypts it if it was encrypted
    async def get(self, key: ObjectKey) -> bytes:
        raw = await self._backend.get(key)
        return _decrypt(raw) if should_encrypt(kind_for(key)) else raw

    # deletes an object
    async def delete(self, key: ObjectKey) -> None:
        await self._backend.delete(key)

    # checks whether an object exists
    async def exists(self, key: ObjectKey) -> bool:
        return await self._backend.exists(key)

    # signs a url that lets the caller upload a new object of an allowed type
    def sign_put_url(
        self,
        *,
        kind: str,
        tenant: str,
        content_type: str,
        ttl_seconds: int,
    ) -> SignedUrl:
        constraint = constraint_for(kind)
        if content_type not in constraint.allowed_content_types:
            raise ValueError(f"content_type not allowed for {kind}")
        key = build_key(tenant=tenant, kind=kind)
        return self._backend.sign_put_url(key, content_type, ttl_seconds)

    # signs a url that lets the caller download an object
    def sign_get_url(self, key: ObjectKey, ttl_seconds: int) -> SignedUrl:
        return self._backend.sign_get_url(key, ttl_seconds)

    # verifies a signed upload request
    async def verify_signed_put(
        self,
        key: ObjectKey,
        content_type: str,
        expires_at: int,
        signature: str,
    ) -> None:
        await self._backend.verify_signed_put(key, content_type, expires_at, signature)

    # verifies a signed download request
    async def verify_signed_get(self, key: ObjectKey, expires_at: int, signature: str) -> None:
        await self._backend.verify_signed_get(key, expires_at, signature)
