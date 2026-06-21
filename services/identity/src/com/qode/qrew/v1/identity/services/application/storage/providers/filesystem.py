import asyncio
import os
from pathlib import Path

from com.qode.qrew.v1.identity.services.application.storage.errors import ObjectNotFoundError
from com.qode.qrew.v1.identity.services.application.storage.security.keys import (
    ObjectKey,
    is_valid_key,
)
from com.qode.qrew.v1.identity.services.application.storage.security.signing import (
    SignedUrl,
    sign,
    verify,
)


class LocalFilesystemBackend:
    """Store objects on the local filesystem under a configurable root."""

    def __init__(
        self,
        *,
        root: str,
        signing_secret: str,
        url_prefix: str = "/v1/uploads/local/",
    ) -> None:
        self._root = Path(root).resolve()
        self._signing_secret = signing_secret
        self._url_prefix = url_prefix.rstrip("/") + "/"
        self._root.mkdir(parents=True, exist_ok=True)

    def _path_for(self, key: ObjectKey) -> Path:
        if not is_valid_key(key):
            raise ValueError("invalid object key")
        candidate = (self._root / key).resolve()
        if not str(candidate).startswith(str(self._root)):
            raise ValueError("invalid object key")
        return candidate

    async def put(self, key: ObjectKey, content: bytes, content_type: str) -> None:
        del content_type
        target = self._path_for(key)
        target.parent.mkdir(parents=True, exist_ok=True)
        tmp = target.with_suffix(target.suffix + ".tmp")
        await asyncio.to_thread(tmp.write_bytes, content)
        await asyncio.to_thread(os.replace, tmp, target)

    async def get(self, key: ObjectKey) -> bytes:
        target = self._path_for(key)
        if not await asyncio.to_thread(target.exists):
            raise ObjectNotFoundError(key)
        return await asyncio.to_thread(target.read_bytes)

    async def delete(self, key: ObjectKey) -> None:
        target = self._path_for(key)
        try:
            await asyncio.to_thread(target.unlink)
        except FileNotFoundError:
            return
        parent = target.parent
        while parent != self._root and parent.exists():
            try:
                await asyncio.to_thread(parent.rmdir)
            except OSError:
                break
            parent = parent.parent

    async def exists(self, key: ObjectKey) -> bool:
        target = self._path_for(key)
        return await asyncio.to_thread(target.exists)

    def sign_put_url(self, key: ObjectKey, content_type: str, ttl_seconds: int) -> SignedUrl:
        expires_at, signature = sign(
            secret=self._signing_secret,
            method="PUT",
            key=key,
            content_type=content_type,
            ttl_seconds=ttl_seconds,
        )
        url = (
            f"{self._url_prefix}{key}"
            f"?expires_at={expires_at}&sig={signature}"
            f"&content_type={content_type}"
        )
        return SignedUrl(url=url, key=key, expires_at=expires_at, content_type=content_type)

    def sign_get_url(self, key: ObjectKey, ttl_seconds: int) -> SignedUrl:
        expires_at, signature = sign(
            secret=self._signing_secret,
            method="GET",
            key=key,
            content_type="",
            ttl_seconds=ttl_seconds,
        )
        url = f"{self._url_prefix}{key}?expires_at={expires_at}&sig={signature}"
        return SignedUrl(url=url, key=key, expires_at=expires_at, content_type=None)

    async def verify_signed_put(
        self,
        key: ObjectKey,
        content_type: str,
        expires_at: int,
        signature: str,
    ) -> None:
        verify(
            secret=self._signing_secret,
            method="PUT",
            key=key,
            content_type=content_type,
            expires_at=expires_at,
            signature=signature,
        )

    async def verify_signed_get(self, key: ObjectKey, expires_at: int, signature: str) -> None:
        verify(
            secret=self._signing_secret,
            method="GET",
            key=key,
            content_type="",
            expires_at=expires_at,
            signature=signature,
        )
