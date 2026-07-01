import enum


class AuditAction(enum.StrEnum):
    GENESIS = "genesis"
    SCANNER_CREATED = "scanner_created"
    SCANNER_ROTATED = "scanner_rotated"
    SCANNER_DEACTIVATED = "scanner_deactivated"
    SCANNER_REFRESH_FAILED = "scanner_refresh_failed"
    ENTRY_VALIDATED = "entry_validated"
    ENTRY_REJECTED = "entry_rejected"
