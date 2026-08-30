# tests the rules a kyc submission has to satisfy before a reviewer sees it
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from cryptography.fernet import Fernet

from com.qode.qrew.v1.identity.models.user import KycStatus
from com.qode.qrew.v1.identity.services.application.authentication.kyc.ocr import OcrError
from com.qode.qrew.v1.identity.services.application.authentication.kyc.submission import (
    KycError,
    KycService,
)

_MODULE = "com.qode.qrew.v1.identity.services.application.authentication.kyc.submission"

DOCUMENT = b"\xff\xd8\xff" + b"0" * 64


# builds settings that keep review manual and give the service a usable key
def _settings(*, auto_approve: bool = False) -> SimpleNamespace:
    return SimpleNamespace(
        national_id_encryption_key=Fernet.generate_key().decode(),
        kyc_auto_approve=auto_approve,
    )


# builds a user in the state under test
def _user(status: KycStatus = KycStatus.not_submitted) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid.uuid4(),
        email="user@example.com",
        full_name="Test User",
        kyc_status=status,
        kyc_document_object_key=None,
        national_id_hash=None,
        national_id_number=None,
        national_id_type=None,
    )


# builds a kyc service whose collaborators are all stand ins
def _make_service(
    *, existing: object = None, scanned: str | None = None
) -> tuple[KycService, MagicMock, MagicMock]:
    repo = MagicMock()
    repo.get_by_national_id_hash = AsyncMock(return_value=existing)
    repo.save = AsyncMock()

    notifier = MagicMock()
    notifier.send_kyc_status_update = AsyncMock()

    audit = MagicMock()
    audit.record = AsyncMock()

    ocr = MagicMock()
    if scanned is None:
        ocr.extract_national_id = MagicMock(side_effect=OcrError("Document number not read."))
    else:
        ocr.extract_national_id = MagicMock(return_value=scanned)

    return KycService(repo, notifier, audit, ocr), repo, notifier


# runs an upload with the storage layer stubbed out
async def _upload(service: KycService, user: object, **kwargs: object) -> KycStatus:
    storage = MagicMock()
    storage.put = AsyncMock(return_value="kyc/object-key")
    storage.delete = AsyncMock()
    with patch(f"{_MODULE}.storage", storage):
        return await service.upload(user, DOCUMENT, **kwargs)  # type: ignore[arg-type]


class TestUploadRefusals:
    # verifies that an approved account cannot submit again
    async def test_refuses_an_approved_account(self) -> None:
        service, _, _ = _make_service()
        with patch(f"{_MODULE}.settings", _settings()), pytest.raises(KycError, match="approved"):
            await _upload(
                service,
                _user(KycStatus.approved),
                document_type="dni",
                document_number="00000001R",
            )

    # verifies that a submission already waiting is not replaced
    async def test_refuses_an_account_already_under_review(self) -> None:
        service, _, _ = _make_service()
        with patch(f"{_MODULE}.settings", _settings()), pytest.raises(KycError, match="review"):
            await _upload(
                service,
                _user(KycStatus.pending),
                document_type="dni",
                document_number="00000001R",
            )

    # verifies that a document whose number does not match its type is refused
    async def test_refuses_a_document_that_fails_its_own_rules(self) -> None:
        service, _, _ = _make_service()
        with patch(f"{_MODULE}.settings", _settings()), pytest.raises(KycError, match="check"):
            await _upload(service, _user(), document_type="dni", document_number="00000001A")

    # verifies that a document already tied to another account is refused
    async def test_refuses_a_document_held_by_another_account(self) -> None:
        service, _, _ = _make_service(existing=SimpleNamespace(id=uuid.uuid4()))
        with patch(f"{_MODULE}.settings", _settings()), pytest.raises(KycError, match="already"):
            await _upload(service, _user(), document_type="dni", document_number="00000001R")


class TestUploadAcceptance:
    # verifies that a spanish document is stored and left for a reviewer
    async def test_accepts_a_dni_and_leaves_it_pending(self) -> None:
        service, repo, notifier = _make_service(scanned="00000001R")
        user = _user()
        with patch(f"{_MODULE}.settings", _settings()):
            status = await _upload(service, user, document_type="dni", document_number="00000001R")
        assert status == KycStatus.pending
        assert user.national_id_type == "dni"
        assert user.national_id_hash is not None
        assert user.kyc_document_object_key == "kyc/object-key"
        repo.save.assert_awaited()
        notifier.send_kyc_status_update.assert_not_awaited()

    # verifies that a passport is accepted even though no scan can read it
    async def test_accepts_a_passport_without_a_readable_scan(self) -> None:
        service, _, _ = _make_service(scanned=None)
        user = _user()
        with patch(f"{_MODULE}.settings", _settings()):
            status = await _upload(
                service, user, document_type="passport", document_number="AB123456"
            )
        assert status == KycStatus.pending
        assert user.national_id_type == "passport"

    # verifies that a scan disagreeing with the declared number does not block the submission
    async def test_accepts_a_dni_whose_scan_disagrees(self) -> None:
        service, _, _ = _make_service(scanned="00000002W")
        user = _user()
        with patch(f"{_MODULE}.settings", _settings()):
            status = await _upload(service, user, document_type="dni", document_number="00000001R")
        assert status == KycStatus.pending

    # verifies that the development shortcut approves and tells the account
    async def test_approves_outright_when_configured_to(self) -> None:
        service, _, notifier = _make_service(scanned="00000001R")
        user = _user()
        with patch(f"{_MODULE}.settings", _settings(auto_approve=True)):
            status = await _upload(service, user, document_type="dni", document_number="00000001R")
        assert status == KycStatus.approved
        notifier.send_kyc_status_update.assert_awaited_once()
