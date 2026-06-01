import uuid
from datetime import datetime

from pydantic import BaseModel

from com.qode.qrew.v1.service.models.audit.audit import AuditAction, AuditEvent

_SUMMARIES: dict[str, str] = {
    AuditAction.REGISTER: "Account registered",
    AuditAction.LOGIN: "Signed in",
    AuditAction.LOGIN_FAILED: "Failed sign-in attempt",
    AuditAction.LOGIN_LOCKED: "Account temporarily locked",
    AuditAction.LOGIN_UNLOCKED: "Account unlocked by support",
    AuditAction.LOGIN_COMPROMISED_PASSWORD: (
        "Sign-in with a password found in a breach database"
    ),
    AuditAction.SESSION_EVICTED: "Older session evicted (session cap)",
    AuditAction.ACCOUNT_DELETED: "Account deleted",
    AuditAction.LOGOUT: "Signed out",
    AuditAction.VERIFY_EMAIL: "Email address verified",
    AuditAction.VERIFY_PHONE: "Phone number verified",
    AuditAction.KYC_UPLOADED: "KYC documents uploaded",
    AuditAction.KYC_REVIEWED: "KYC reviewed",
    AuditAction.PASSKEY_REGISTERED: "Passkey added",
    AuditAction.PASSKEY_AUTHENTICATED: "Signed in with passkey",
    AuditAction.PASSKEY_DELETED: "Passkey removed",
    AuditAction.PASSKEY_RENAMED: "Passkey renamed",
    AuditAction.PASSKEY_REASSERTED: "Identity re-verified",
    AuditAction.TOKEN_REFRESHED: "Session refreshed",
    AuditAction.TOKEN_THEFT_DETECTED: "Possible token theft detected",
    AuditAction.SETUP_COMPLETED: "Onboarding complete",
    AuditAction.PASSWORD_CHANGED: "Password changed",
    AuditAction.EMAIL_CHANGE_REQUESTED: "Email change requested",
    AuditAction.EMAIL_CHANGE_CONFIRMED: "Email address changed",
    AuditAction.PHONE_CHANGE_REQUESTED: "Phone change requested",
    AuditAction.PHONE_CHANGE_CONFIRMED: "Phone number changed",
    AuditAction.RECOVERY_BEGIN: "Account recovery started",
    AuditAction.RECOVERY_COMPLETED: "Account recovery completed",
    AuditAction.RECOVERY_FAILED: "Account recovery failed",
    AuditAction.LOGIN_ANOMALY_DETECTED: "Unusual sign-in flagged",
    AuditAction.DEVICE_BIND: "Device bound",
    AuditAction.DEVICE_REVOKE: "Device revoked",
    AuditAction.DEVICE_REVOKE_ALL: "All devices revoked",
    AuditAction.DEVICE_ATTESTED: "Device integrity verified",
    AuditAction.DEVICE_ATTESTATION_FAILED: "Device integrity check failed",
    AuditAction.SCANNER_CREATED: "Scanner registered",
    AuditAction.SCANNER_ROTATED: "Scanner credential rotated",
    AuditAction.SCANNER_DEACTIVATED: "Scanner deactivated",
    AuditAction.FINGERPRINT_MULTI_ACCOUNT_FLAG: "Device flagged: multiple accounts",
    AuditAction.FINGERPRINT_HEADLESS_FLAG: "Device flagged: automation detected",
}


def summarize(action: str) -> str:
    return _SUMMARIES.get(action, action.replace("_", " ").capitalize())


class UserAuditEventResponse(BaseModel):
    id: uuid.UUID
    action: str
    entity_type: str | None
    summary: str
    ip_address: str | None
    device_fingerprint_hash: str | None
    created_at: datetime

    @classmethod
    def from_event(cls, event: AuditEvent) -> "UserAuditEventResponse":
        return cls(
            id=event.id,
            action=event.action,
            entity_type=event.entity_type,
            summary=summarize(event.action),
            ip_address=event.ip_address,
            device_fingerprint_hash=event.device_fingerprint_hash,
            created_at=event.created_at,
        )
