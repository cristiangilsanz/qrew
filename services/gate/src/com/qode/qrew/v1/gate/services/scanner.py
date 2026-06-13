import uuid
from datetime import UTC, date as date_type, datetime

import structlog

from com.qode.qrew.v1.gate.core.infra.errors import DomainError
from com.qode.qrew.v1.gate.core.scanner.security import create_scanner_token
from com.qode.qrew.v1.gate.models.audit import AuditAction
from com.qode.qrew.v1.gate.models.scanner import Scanner
from com.qode.qrew.v1.gate.repositories.scanner import ScannerRepository
from com.qode.qrew.v1.gate.services.audit import AuditService
from com.qode.qrew.v1.gate.settings import settings

logger = structlog.get_logger(__name__)


class ScannerError(DomainError):
    pass


class ScannerService:
    def __init__(self, repo: ScannerRepository, audit: AuditService) -> None:
        self._repo = repo
        self._audit = audit

    async def create(
        self,
        admin_id: uuid.UUID,
        name: str,
        venue_id: uuid.UUID,
        event_id: uuid.UUID,
        scan_date: date_type,
    ) -> tuple[Scanner, str]:
        scanner = await self._repo.create(
            Scanner(id=uuid.uuid4(), name=name, venue_id=venue_id, created_by=admin_id)
        )
        token = create_scanner_token(scanner.id, venue_id, event_id, scan_date.isoformat())
        await logger.ainfo("scanner_created", scanner_id=str(scanner.id))
        try:
            await self._audit.record(
                action=AuditAction.SCANNER_CREATED,
                actor_id=admin_id,
                entity_type="scanner",
                entity_id=str(scanner.id),
                payload={"venue_id": str(venue_id), "event_id": str(event_id)},
            )
        except Exception:
            await logger.awarning("audit_write_failed", action=AuditAction.SCANNER_CREATED)
        return scanner, token

    async def list_all(self) -> list[Scanner]:
        return await self._repo.list_all()

    async def rotate(
        self,
        admin_id: uuid.UUID,
        scanner_id: uuid.UUID,
        venue_id: uuid.UUID,
        event_id: uuid.UUID,
        scan_date: date_type,
    ) -> tuple[Scanner, str]:
        scanner = await self._repo.get_by_id(scanner_id)
        if scanner is None:
            raise ScannerError("Scanner not found", field="scanner_id")
        if not scanner.is_active:
            raise ScannerError("Scanner is deactivated", field="scanner_id")
        if scanner.venue_id != venue_id:
            raise ScannerError("Scanner is registered to a different venue", field="venue_id")
        token = create_scanner_token(scanner.id, venue_id, event_id, scan_date.isoformat())
        try:
            await self._audit.record(
                action=AuditAction.SCANNER_ROTATED,
                actor_id=admin_id,
                entity_type="scanner",
                entity_id=str(scanner.id),
                payload={"event_id": str(event_id)},
            )
        except Exception:
            await logger.awarning("audit_write_failed", action=AuditAction.SCANNER_ROTATED)
        return scanner, token

    async def deactivate(self, admin_id: uuid.UUID, scanner_id: uuid.UUID) -> Scanner:
        scanner = await self._repo.get_by_id(scanner_id)
        if scanner is None:
            raise ScannerError("Scanner not found", field="scanner_id")
        if not scanner.is_active:
            raise ScannerError("Scanner already deactivated", field="scanner_id")
        scanner = await self._repo.deactivate(scanner)
        await logger.ainfo("scanner_deactivated", scanner_id=str(scanner.id))
        try:
            await self._audit.record(
                action=AuditAction.SCANNER_DEACTIVATED,
                actor_id=admin_id,
                entity_type="scanner",
                entity_id=str(scanner.id),
            )
        except Exception:
            await logger.awarning("audit_write_failed", action=AuditAction.SCANNER_DEACTIVATED)
        return scanner

    async def refresh_self(
        self,
        scanner_id: uuid.UUID,
        venue_id: uuid.UUID,
        event_id: uuid.UUID,
        scan_date: date_type,
    ) -> tuple[Scanner, str]:
        scanner = await self._repo.get_by_id(scanner_id)
        if scanner is None or not scanner.is_active:
            await self._record_refresh_failure(scanner_id, reason="scanner_inactive")
            raise ScannerError("Scanner is not active", field="scanner_id")
        if scanner.venue_id != venue_id:
            await self._record_refresh_failure(scanner_id, reason="venue_mismatch")
            raise ScannerError("Refresh scope does not match registration", field="venue_id")
        token = create_scanner_token(scanner.id, venue_id, event_id, scan_date.isoformat())
        scanner.last_refreshed_at = datetime.now(UTC)
        await self._repo.save(scanner)
        try:
            await self._audit.record(
                action=AuditAction.SCANNER_ROTATED,
                actor_id=scanner.id,
                entity_type="scanner",
                entity_id=str(scanner.id),
                payload={"event_id": str(event_id), "self_refresh": True},
            )
        except Exception:
            await logger.awarning("audit_write_failed", action=AuditAction.SCANNER_ROTATED)
        return scanner, token

    async def get_by_id(self, scanner_id: uuid.UUID) -> Scanner:
        scanner = await self._repo.get_by_id(scanner_id)
        if scanner is None:
            raise ScannerError("Scanner not found", field="scanner_id")
        return scanner

    async def _record_refresh_failure(self, scanner_id: uuid.UUID, *, reason: str) -> None:
        try:
            await self._audit.record(
                action=AuditAction.SCANNER_REFRESH_FAILED,
                actor_id=scanner_id,
                entity_type="scanner",
                entity_id=str(scanner_id),
                payload={"reason": reason},
            )
        except Exception:
            await logger.awarning("audit_write_failed", action=AuditAction.SCANNER_REFRESH_FAILED)

    @property
    def token_ttl_hours(self) -> int:
        return settings.scanner_token_expire_hours
