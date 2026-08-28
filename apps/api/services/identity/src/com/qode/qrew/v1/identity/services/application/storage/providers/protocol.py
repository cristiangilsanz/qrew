# defines the interface every storage backend must implement
from typing import Protocol

from com.qode.qrew.v1.identity.services.application.storage.security.keys import ObjectKey
from com.qode.qrew.v1.identity.services.application.storage.security.signing import SignedUrl


class StorageBackend(Protocol):
    # writes an object to the backend
    async def put(self, key: ObjectKey, content: bytes, content_type: str) -> None: ...

    # reads an object from the backend
    async def get(self, key: ObjectKey) -> bytes: ...

    # deletes an object from the backend
    async def delete(self, key: ObjectKey) -> None: ...

    # checks whether an object exists in the backend
    async def exists(self, key: ObjectKey) -> bool: ...

    # signs a url that lets the caller upload an object
    def sign_put_url(self, key: ObjectKey, content_type: str, ttl_seconds: int) -> SignedUrl: ...

    # signs a url that lets the caller download an object
    def sign_get_url(self, key: ObjectKey, ttl_seconds: int) -> SignedUrl: ...

    # verifies a signed upload request
    async def verify_signed_put(
        self,
        key: ObjectKey,
        content_type: str,
        expires_at: int,
        signature: str,
    ) -> None: ...

    # verifies a signed download request
    async def verify_signed_get(self, key: ObjectKey, expires_at: int, signature: str) -> None: ...
