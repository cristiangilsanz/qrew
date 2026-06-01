from pathlib import Path

import pytest

from com.qode.qrew.v1.service.core.storage.encryption import (
    ENCRYPTED_KINDS,
    decrypt,
)
from com.qode.qrew.v1.service.core.storage.keys import is_known_kind
from com.qode.qrew.v1.service.core.storage.local import LocalFilesystemBackend
from com.qode.qrew.v1.service.core.storage.service import StorageService


@pytest.fixture
def service(tmp_path: Path) -> tuple[StorageService, Path]:
    backend = LocalFilesystemBackend(root=str(tmp_path), signing_secret="s")
    return StorageService(backend), tmp_path


async def test_known_kinds_match_allowlist() -> None:
    for kind in ("kyc", "event_image", "scanner_photo"):
        assert is_known_kind(kind)
    assert not is_known_kind("random")


async def test_kyc_put_writes_ciphertext_to_disk(
    service: tuple[StorageService, Path],
) -> None:
    svc, root = service
    key = await svc.put(
        kind="kyc",
        tenant="user:u1",
        content=b"the original document",
        content_type="image/jpeg",
    )
    on_disk = (root / key).read_bytes()
    assert on_disk != b"the original document"
    assert decrypt(on_disk) == b"the original document"


async def test_get_decrypts_kyc_transparently(
    service: tuple[StorageService, Path],
) -> None:
    svc, _ = service
    key = await svc.put(
        kind="kyc",
        tenant="user:u1",
        content=b"the original document",
        content_type="image/jpeg",
    )
    assert await svc.get(key) == b"the original document"


async def test_unknown_kind_rejected(service: tuple[StorageService, Path]) -> None:
    svc, _ = service
    with pytest.raises(ValueError, match="unknown kind"):
        await svc.put(kind="bogus", tenant="user:u1", content=b"x", content_type="x")


async def test_encrypted_kinds_only_includes_kyc() -> None:
    assert frozenset({"kyc"}) == ENCRYPTED_KINDS


async def test_sign_put_url_rejects_bad_content_type(
    service: tuple[StorageService, Path],
) -> None:
    svc, _ = service
    with pytest.raises(ValueError, match="content_type"):
        svc.sign_put_url(
            kind="kyc",
            tenant="user:u1",
            content_type="text/plain",
            ttl_seconds=60,
        )
