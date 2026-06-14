from typing import Protocol

from com.qode.qrew.v1.identity.services.storage.keys import ObjectKey
from com.qode.qrew.v1.identity.services.storage.signing import SignedUrl


class StorageBackend(Protocol):
    """Common interface every storage backend must satisfy."""

    async def put(self, key: ObjectKey, content: bytes, content_type: str) -> None: ...

    async def get(self, key: ObjectKey) -> bytes: ...

    async def delete(self, key: ObjectKey) -> None: ...

    async def exists(self, key: ObjectKey) -> bool: ...

    def sign_put_url(self, key: ObjectKey, content_type: str, ttl_seconds: int) -> SignedUrl: ...

    def sign_get_url(self, key: ObjectKey, ttl_seconds: int) -> SignedUrl: ...

    async def verify_signed_put(
        self,
        key: ObjectKey,
        content_type: str,
        expires_at: int,
        signature: str,
    ) -> None: ...

    async def verify_signed_get(self, key: ObjectKey, expires_at: int, signature: str) -> None: ...
