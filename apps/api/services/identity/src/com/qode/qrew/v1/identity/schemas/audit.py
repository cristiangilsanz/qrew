# defines the response schema for a user's audit trail entries
import uuid
from typing import TYPE_CHECKING
from datetime import datetime

from pydantic import BaseModel

from com.qode.qrew.v1.identity.models.audit import AuditAction

_SUMMARIES: dict[str, str] = {
    AuditAction.REGISTER: "Account Registered",
    AuditAction.LOGIN: "Signed In",
    AuditAction.LOGIN_FAILED: "Sign In Failed",
    AuditAction.LOGIN_LOCKED: "Account Locked",
    AuditAction.LOGIN_UNLOCKED: "Account Unlocked",
    AuditAction.LOGIN_COMPROMISED_PASSWORD: "Breached Password Used",
    AuditAction.SESSION_EVICTED: "Older Session Evicted",
    AuditAction.ACCOUNT_DELETED: "Account Deleted",
    AuditAction.LOGOUT: "Signed Out",
    AuditAction.VERIFY_EMAIL: "Email Verified",
    AuditAction.VERIFY_PHONE: "Phone Verified",
    AuditAction.KYC_UPLOADED: "Document Uploaded",
    AuditAction.KYC_REVIEWED: "Document Reviewed",
    AuditAction.PASSKEY_REGISTERED: "Passkey Added",
    AuditAction.PASSKEY_AUTHENTICATED: "Signed In With Passkey",
    AuditAction.PASSKEY_DELETED: "Passkey Removed",
    AuditAction.PASSKEY_RENAMED: "Passkey Renamed",
    AuditAction.PASSKEY_REASSERTED: "Identity Reverified",
    AuditAction.TOKEN_REFRESHED: "Session Refreshed",
    AuditAction.TOKEN_THEFT_DETECTED: "Token Theft Detected",
    AuditAction.SETUP_COMPLETED: "Onboarding Completed",
    AuditAction.PASSWORD_CHANGED: "Password Changed",
    AuditAction.EMAIL_CHANGE_REQUESTED: "Email Change Requested",
    AuditAction.EMAIL_CHANGE_CONFIRMED: "Email Changed",
    AuditAction.PHONE_CHANGE_REQUESTED: "Phone Change Requested",
    AuditAction.PHONE_CHANGE_CONFIRMED: "Phone Changed",
    AuditAction.RECOVERY_BEGIN: "Recovery Started",
    AuditAction.RECOVERY_COMPLETED: "Recovery Completed",
    AuditAction.RECOVERY_FAILED: "Recovery Failed",
    AuditAction.LOGIN_ANOMALY_DETECTED: "Unusual Sign In",
    AuditAction.DEVICE_BIND: "Device Bound",
    AuditAction.DEVICE_REVOKE: "Device Revoked",
    AuditAction.DEVICE_REVOKE_ALL: "All Devices Revoked",
    AuditAction.DEVICE_ATTESTED: "Device Verified",
    AuditAction.DEVICE_ATTESTATION_FAILED: "Device Check Failed",
    AuditAction.SCANNER_CREATED: "Scanner Registered",
    AuditAction.SCANNER_ROTATED: "Scanner Credential Rotated",
    AuditAction.SCANNER_DEACTIVATED: "Scanner Deactivated",
    AuditAction.FINGERPRINT_MULTI_ACCOUNT_FLAG: "Multiple Accounts Flagged",
    AuditAction.FINGERPRINT_HEADLESS_FLAG: "Automation Flagged",
    AuditAction.TOTP_ENABLED: "Two Factor Enabled",
    AuditAction.TOTP_DISABLED: "Two Factor Disabled",
    AuditAction.TOTP_VERIFIED: "Signed In With Two Factor",
    AuditAction.TOTP_VERIFY_FAILED: "Two Factor Failed",
    AuditAction.TOTP_BACKUP_USED: "Backup Code Used",
}


# turns an audit action into a human readable summary
def summarize(action: str) -> str:
    return _SUMMARIES.get(action, action.replace("_", " ").title())


if TYPE_CHECKING:
    from com.qode.qrew.v1.identity.services.application.trail import AuditTrailEntry


class UserAuditEventResponse(BaseModel):
    id: uuid.UUID
    action: str
    entity_type: str | None
    summary: str
    ip_address: str | None
    device_fingerprint_hash: str | None
    created_at: datetime

    # converts an audit trail entry into its response
    @classmethod
    def from_event(cls, event: "AuditTrailEntry") -> "UserAuditEventResponse":
        return cls(
            id=event.id,
            action=event.action,
            entity_type=event.entity_type,
            summary=summarize(event.action),
            ip_address=event.ip_address,
            device_fingerprint_hash=event.device_fingerprint_hash,
            created_at=event.created_at,
        )
