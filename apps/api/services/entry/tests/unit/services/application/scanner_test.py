import uuid
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from conftest import make_scanner

from com.qode.qrew.v1.entry.services.application.scanner import (
    ScannerError,
    ScannerService,
)

_PATCH_CREATE_TOKEN = (
    "com.qode.qrew.v1.entry.services.application.scanner.create_scanner_token"
)
_PATCH_SETTINGS = "com.qode.qrew.v1.entry.services.application.scanner.settings"


def _make_svc(
    *,
    scanner: object = None,
    scanners: list | None = None,
) -> tuple[ScannerService, MagicMock, MagicMock]:
    repo = MagicMock()
    repo.create = AsyncMock(side_effect=lambda s: s)
    repo.get_by_id = AsyncMock(return_value=scanner)
    repo.list_all = AsyncMock(return_value=scanners or [])
    repo.deactivate = AsyncMock(side_effect=lambda s: s)
    repo.save = AsyncMock(side_effect=lambda s: s)

    audit = AsyncMock()
    audit.record = AsyncMock()

    svc = ScannerService(repo=repo, audit=audit)
    return svc, repo, audit


def _fake_settings() -> MagicMock:
    s = MagicMock()
    s.scanner_token_expire_hours = 8
    return s


class TestScannerServiceCreate:
    async def test_creates_scanner_and_returns_token(
        self, admin_id: uuid.UUID, venue_id: uuid.UUID, event_id: uuid.UUID
    ) -> None:
        svc, repo, _ = _make_svc()
        with patch(_PATCH_CREATE_TOKEN, return_value="tok.abc") as mock_token:
            scanner, token = await svc.create(
                admin_id, "Gate 1", venue_id, event_id, date(2026, 8, 1)
            )
        assert token == "tok.abc"
        assert scanner.name == "Gate 1"
        assert scanner.venue_id == venue_id
        mock_token.assert_called_once_with(scanner.id, venue_id, event_id, "2026-08-01")
        repo.create.assert_awaited_once()

    async def test_audit_swallows_errors(
        self, admin_id: uuid.UUID, venue_id: uuid.UUID, event_id: uuid.UUID
    ) -> None:
        svc, _, audit = _make_svc()
        audit.record = AsyncMock(side_effect=RuntimeError("audit down"))
        with patch(_PATCH_CREATE_TOKEN, return_value="tok"):
            scanner, _ = await svc.create(
                admin_id, "Gate 1", venue_id, event_id, date(2026, 8, 1)
            )
        assert scanner is not None


class TestScannerServiceRotate:
    async def test_raises_when_not_found(
        self, admin_id: uuid.UUID, venue_id: uuid.UUID, event_id: uuid.UUID
    ) -> None:
        svc, _, _ = _make_svc(scanner=None)
        with pytest.raises(ScannerError, match="not found"):
            await svc.rotate(
                admin_id, uuid.uuid4(), venue_id, event_id, date(2026, 8, 1)
            )

    async def test_raises_when_scanner_inactive(
        self, admin_id: uuid.UUID, venue_id: uuid.UUID, event_id: uuid.UUID
    ) -> None:
        scanner = make_scanner(venue_id=venue_id, is_active=False)
        svc, _, _ = _make_svc(scanner=scanner)
        with pytest.raises(ScannerError, match="deactivated"):
            await svc.rotate(admin_id, scanner.id, venue_id, event_id, date(2026, 8, 1))

    async def test_raises_when_venue_mismatch(
        self, admin_id: uuid.UUID, venue_id: uuid.UUID, event_id: uuid.UUID
    ) -> None:
        scanner = make_scanner(venue_id=uuid.uuid4())  # different venue
        svc, _, _ = _make_svc(scanner=scanner)
        with pytest.raises(ScannerError, match="different venue"):
            await svc.rotate(admin_id, scanner.id, venue_id, event_id, date(2026, 8, 1))

    async def test_returns_scanner_and_token(
        self, admin_id: uuid.UUID, venue_id: uuid.UUID, event_id: uuid.UUID
    ) -> None:
        scanner = make_scanner(venue_id=venue_id)
        svc, _, _ = _make_svc(scanner=scanner)
        with patch(_PATCH_CREATE_TOKEN, return_value="rotated.tok"):
            result, token = await svc.rotate(
                admin_id, scanner.id, venue_id, event_id, date(2026, 8, 1)
            )
        assert result is scanner
        assert token == "rotated.tok"


class TestScannerServiceDeactivate:
    async def test_raises_when_not_found(self, admin_id: uuid.UUID) -> None:
        svc, _, _ = _make_svc(scanner=None)
        with pytest.raises(ScannerError, match="not found"):
            await svc.deactivate(admin_id, uuid.uuid4())

    async def test_raises_when_already_deactivated(self, admin_id: uuid.UUID) -> None:
        scanner = make_scanner(is_active=False)
        svc, _, _ = _make_svc(scanner=scanner)
        with pytest.raises(ScannerError, match="already deactivated"):
            await svc.deactivate(admin_id, scanner.id)

    async def test_returns_deactivated_scanner(self, admin_id: uuid.UUID) -> None:
        scanner = make_scanner(is_active=True)
        svc, repo, _ = _make_svc(scanner=scanner)
        result = await svc.deactivate(admin_id, scanner.id)
        assert result is scanner
        repo.deactivate.assert_awaited_once_with(scanner)


class TestScannerServiceRefreshSelf:
    async def test_raises_when_scanner_not_found(
        self, venue_id: uuid.UUID, event_id: uuid.UUID
    ) -> None:
        svc, _, _ = _make_svc(scanner=None)
        with pytest.raises(ScannerError, match="not active"):
            await svc.refresh_self(uuid.uuid4(), venue_id, event_id, date(2026, 8, 1))

    async def test_raises_when_scanner_inactive(
        self, venue_id: uuid.UUID, event_id: uuid.UUID
    ) -> None:
        scanner = make_scanner(venue_id=venue_id, is_active=False)
        svc, _, _ = _make_svc(scanner=scanner)
        with pytest.raises(ScannerError, match="not active"):
            await svc.refresh_self(scanner.id, venue_id, event_id, date(2026, 8, 1))

    async def test_raises_when_venue_mismatch(self, event_id: uuid.UUID) -> None:
        scanner = make_scanner(venue_id=uuid.uuid4())
        svc, _, _ = _make_svc(scanner=scanner)
        with pytest.raises(ScannerError, match="Refresh scope"):
            await svc.refresh_self(scanner.id, uuid.uuid4(), event_id, date(2026, 8, 1))

    async def test_returns_scanner_and_token(
        self, venue_id: uuid.UUID, event_id: uuid.UUID
    ) -> None:
        scanner = make_scanner(venue_id=venue_id)
        svc, repo, _ = _make_svc(scanner=scanner)
        with patch(_PATCH_CREATE_TOKEN, return_value="refresh.tok"):
            result, token = await svc.refresh_self(
                scanner.id, venue_id, event_id, date(2026, 8, 1)
            )
        assert result is scanner
        assert token == "refresh.tok"
        assert scanner.last_refreshed_at is not None
        repo.save.assert_awaited_once()


class TestScannerServiceGetById:
    async def test_raises_when_not_found(self) -> None:
        svc, _, _ = _make_svc(scanner=None)
        with pytest.raises(ScannerError, match="not found"):
            await svc.get_by_id(uuid.uuid4())

    async def test_returns_scanner(self) -> None:
        scanner = make_scanner()
        svc, _, _ = _make_svc(scanner=scanner)
        result = await svc.get_by_id(scanner.id)
        assert result is scanner

    async def test_token_ttl_hours_from_settings(self) -> None:
        svc, _, _ = _make_svc()
        with patch(_PATCH_SETTINGS, _fake_settings()):
            assert svc.token_ttl_hours == 8
