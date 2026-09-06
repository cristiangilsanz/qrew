# sets up verifies and disables two factor authentication and its backup codes
import json
import secrets

import pyotp
import structlog
from passlib.context import CryptContext

from com.qode.qrew.v1.identity.models.audit import AuditAction
from com.qode.qrew.v1.identity.models.user import User
from com.qode.qrew.v1.identity.repositories.user import UserRepository
from com.qode.qrew.v1.identity.services.application.audit import AuditService

logger = structlog.get_logger(__name__)

_BACKUP_COUNT = 10
_BACKUP_LEN = 10
_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")


# hashes a backup code for storage
def _hash_backup(code: str) -> str:
    return _pwd.hash(code)  # type: ignore[no-any-return]


# checks a backup code against its stored hash
def _verify_backup(code: str, hashed: str) -> bool:
    return _pwd.verify(code, hashed)  # type: ignore[no-any-return]


class TotpError(Exception):
    # stores the error message
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class TotpService:
    # stores the repository and audit service the totp service uses
    def __init__(self, repo: UserRepository, audit: AuditService | None = None) -> None:
        self._repo = repo
        self._audit = audit or AuditService()

    # generates a new totp secret provisioning uri and backup codes
    def generate_setup(self, user: User, issuer: str = "QREW") -> tuple[str, str, list[str]]:
        secret = pyotp.random_base32()
        totp = pyotp.TOTP(secret)
        uri: str = totp.provisioning_uri(name=user.email, issuer_name=issuer)  # type: ignore[assignment]
        backup_codes = [secrets.token_hex(_BACKUP_LEN // 2) for _ in range(_BACKUP_COUNT)]
        return secret, uri, backup_codes

    # verifies the first code and enables two factor authentication
    async def confirm(self, user: User, secret: str, code: str, backup_codes: list[str]) -> None:
        totp = pyotp.TOTP(secret)
        if not totp.verify(code, valid_window=2):
            raise TotpError("Code rejected.")
        hashed_backups = [_hash_backup(c) for c in backup_codes]
        user.totp_secret = secret
        user.totp_enabled = True
        user.totp_backup_codes_json = json.dumps(hashed_backups)
        await self._repo.save(user)
        await self._audit.record(
            action=AuditAction.TOTP_ENABLED,
            actor_id=user.id,
            entity_type="user",
            entity_id=str(user.id),
        )

    # verifies a totp code or a backup code during a login challenge
    async def verify_login(self, user: User, code: str) -> None:
        if not user.totp_enabled or user.totp_secret is None:
            raise TotpError("Two-factor authentication not enabled.")
        totp = pyotp.TOTP(user.totp_secret)
        if totp.verify(code, valid_window=2):
            await self._audit.record(
                action=AuditAction.TOTP_VERIFIED,
                actor_id=user.id,
                entity_type="user",
                entity_id=str(user.id),
            )
            return
        if user.totp_backup_codes_json:
            hashed_list: list[str] = json.loads(user.totp_backup_codes_json)
            for i, hashed in enumerate(hashed_list):
                if _verify_backup(code, hashed):
                    hashed_list.pop(i)
                    user.totp_backup_codes_json = json.dumps(hashed_list)
                    await self._repo.save(user)
                    await self._audit.record(
                        action=AuditAction.TOTP_BACKUP_USED,
                        actor_id=user.id,
                        entity_type="user",
                        entity_id=str(user.id),
                        payload={"remaining_backup_codes": len(hashed_list)},
                    )
                    return
        await logger.awarning("totp_verify_failed", user_id=str(user.id))
        await self._audit.record(
            action=AuditAction.TOTP_VERIFY_FAILED,
            actor_id=user.id,
            entity_type="user",
            entity_id=str(user.id),
        )
        raise TotpError("Code rejected.")

    # disables two factor authentication after verifying a code
    async def disable(self, user: User, code: str) -> None:
        if not user.totp_enabled or user.totp_secret is None:
            raise TotpError("Two-factor authentication not enabled.")
        totp = pyotp.TOTP(user.totp_secret)
        if not totp.verify(code, valid_window=1):
            raise TotpError("Code rejected.")
        user.totp_secret = None
        user.totp_enabled = False
        user.totp_backup_codes_json = None
        await self._repo.save(user)
        await self._audit.record(
            action=AuditAction.TOTP_DISABLED,
            actor_id=user.id,
            entity_type="user",
            entity_id=str(user.id),
        )
