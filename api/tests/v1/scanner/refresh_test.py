import uuid
from datetime import date
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from com.qode.qrew.v1.service.core.scanner.security import (
    create_scanner_token,
    decode_scanner_token_for_refresh,
)
from com.qode.qrew.v1.service.models.audit.audit import AuditAction
from com.qode.qrew.v1.service.services.scanner.scanner import (
    ScannerError,
    ScannerService,
)


def _mock_scanner(*, venue_id: uuid.UUID, active: bool = True) -> MagicMock:
    s = MagicMock()
    s.id = uuid.uuid4()
    s.venue_id = venue_id
    s.is_active = active
    s.last_refreshed_at = None
    return s


def _service(scanner: Any) -> tuple[ScannerService, MagicMock]:
    repo = MagicMock()
    repo.get_by_id = AsyncMock(return_value=scanner)

    async def _save(s: Any) -> Any:
        return s

    repo.save = AsyncMock(side_effect=_save)
    audit = MagicMock()
    audit.record = AsyncMock()
    return ScannerService(repo, audit), audit


async def test_refresh_self_mints_new_jwt_with_same_scoping() -> None:
    venue_id = uuid.uuid4()
    event_id = uuid.uuid4()
    scan_date = date(2026, 7, 1)
    scanner = _mock_scanner(venue_id=venue_id)
    service, audit = _service(scanner)
    refreshed, token = await service.refresh_self(
        scanner.id, venue_id, event_id, scan_date
    )
    assert refreshed is scanner
    payload = decode_scanner_token_for_refresh(token)
    assert payload["scanner_id"] == str(scanner.id)
    assert payload["venue_id"] == str(venue_id)
    assert payload["event_id"] == str(event_id)
    assert payload["date"] == scan_date.isoformat()
    assert payload.get("aud") == "qrew.scan"
    actions = {c.kwargs["action"] for c in audit.record.await_args_list}
    assert AuditAction.SCANNER_ROTATED in actions
    assert scanner.last_refreshed_at is not None


async def test_refresh_self_rejects_deactivated_scanner() -> None:
    venue_id = uuid.uuid4()
    scanner = _mock_scanner(venue_id=venue_id, active=False)
    service, audit = _service(scanner)
    with pytest.raises(ScannerError):
        await service.refresh_self(scanner.id, venue_id, uuid.uuid4(), date(2026, 7, 1))
    actions = {c.kwargs["action"] for c in audit.record.await_args_list}
    assert AuditAction.SCANNER_REFRESH_FAILED in actions


async def test_refresh_self_rejects_venue_mismatch() -> None:
    scanner = _mock_scanner(venue_id=uuid.uuid4())
    service, audit = _service(scanner)
    with pytest.raises(ScannerError):
        await service.refresh_self(
            scanner.id, uuid.uuid4(), uuid.uuid4(), date(2026, 7, 1)
        )
    actions = {c.kwargs["action"] for c in audit.record.await_args_list}
    assert AuditAction.SCANNER_REFRESH_FAILED in actions


async def test_refresh_self_handles_missing_scanner() -> None:
    repo = MagicMock()
    repo.get_by_id = AsyncMock(return_value=None)
    audit = MagicMock()
    audit.record = AsyncMock()
    service = ScannerService(repo, audit)
    with pytest.raises(ScannerError):
        await service.refresh_self(
            uuid.uuid4(), uuid.uuid4(), uuid.uuid4(), date(2026, 7, 1)
        )


def test_decode_for_refresh_tolerates_expired_signature() -> None:
    token = create_scanner_token(uuid.uuid4(), uuid.uuid4(), uuid.uuid4(), "2026-07-01")
    payload = decode_scanner_token_for_refresh(token)
    assert payload["type"] == "scanner"
    assert payload["aud"] == "qrew.scan"
    assert isinstance(payload["iat"], int)
