# tests that account recovery matches the document against the stored hash
import hashlib
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from com.qode.qrew.v1.identity.core.utils import pii as pii_crypto
from com.qode.qrew.v1.identity.services.application.authentication.account.recovery import (
    RecoveryService,
)

DOCUMENT = b"\xff\xd8\xff" + b"0" * 64
NUMBER = "00000001R"


# builds a recovery service whose collaborators are all stand ins
def _make_service(*, found: object, scanned: str) -> RecoveryService:
    user_repo = MagicMock()
    user_repo.get_by_email = AsyncMock(return_value=found)
    ocr = MagicMock()
    ocr.extract_national_id = MagicMock(return_value=scanned)
    audit = MagicMock()
    audit.record = AsyncMock()
    return RecoveryService(
        user_repo,
        MagicMock(),
        MagicMock(),
        MagicMock(),
        MagicMock(),
        MagicMock(),
        audit,
        ocr,
    )


# builds an account holding the hash of its national identity number
def _user(national_id_hash: str | None) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid.uuid4(),
        email="user@example.com",
        is_active=True,
        national_id_hash=national_id_hash,
    )


class TestVerifyIdentity:
    # verifies that a document matching the stored hash recovers the account
    async def test_accepts_the_number_behind_the_stored_hash(self) -> None:
        user = _user(pii_crypto.hash_lookup(NUMBER))
        service = _make_service(found=user, scanned=NUMBER)
        assert await service._verify_identity("user@example.com", DOCUMENT) is user

    # verifies that the bare digest the column never holds is not accepted
    async def test_refuses_a_bare_sha256_of_the_same_number(self) -> None:
        user = _user(hashlib.sha256(NUMBER.encode()).hexdigest())
        service = _make_service(found=user, scanned=NUMBER)
        assert await service._verify_identity("user@example.com", DOCUMENT) is None

    # verifies that another person's document is refused
    async def test_refuses_a_document_belonging_to_someone_else(self) -> None:
        user = _user(pii_crypto.hash_lookup("00000002W"))
        service = _make_service(found=user, scanned=NUMBER)
        assert await service._verify_identity("user@example.com", DOCUMENT) is None
