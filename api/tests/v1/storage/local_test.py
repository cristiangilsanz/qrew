from pathlib import Path

import pytest

from com.qode.qrew.v1.service.core.storage.errors import ObjectNotFoundError
from com.qode.qrew.v1.service.core.storage.keys import build_key
from com.qode.qrew.v1.service.core.storage.local import LocalFilesystemBackend


@pytest.fixture
def backend(tmp_path: Path) -> LocalFilesystemBackend:
    return LocalFilesystemBackend(root=str(tmp_path), signing_secret="s")


async def test_put_get_roundtrip(backend: LocalFilesystemBackend) -> None:
    key = build_key(tenant="user:u1", kind="kyc")
    await backend.put(key, b"hello", "image/jpeg")
    assert await backend.exists(key)
    assert await backend.get(key) == b"hello"


async def test_delete_removes_object(backend: LocalFilesystemBackend) -> None:
    key = build_key(tenant="user:u1", kind="kyc")
    await backend.put(key, b"hello", "image/jpeg")
    await backend.delete(key)
    assert not await backend.exists(key)


async def test_get_missing_raises(backend: LocalFilesystemBackend) -> None:
    key = build_key(tenant="user:u1", kind="kyc")
    with pytest.raises(ObjectNotFoundError):
        await backend.get(key)


async def test_invalid_key_rejected(backend: LocalFilesystemBackend) -> None:
    with pytest.raises(ValueError, match="invalid object key"):
        await backend.put("../escape/path", b"x", "image/jpeg")


async def test_signed_put_roundtrip(backend: LocalFilesystemBackend) -> None:
    key = build_key(tenant="user:u1", kind="kyc")
    signed = backend.sign_put_url(key, "image/jpeg", ttl_seconds=60)
    await backend.verify_signed_put(
        key,
        "image/jpeg",
        signed.expires_at,
        signed.url.split("&sig=", 1)[1].split("&", 1)[0],
    )
