import json
import secrets

import pyotp
from passlib.context import CryptContext

from com.qode.qrew.v1.identity.models.audit import AuditAction
from com.qode.qrew.v1.identity.models.user import User
from com.qode.qrew.v1.identity.repositories.user import UserRepository
from com.qode.qrew.v1.identity.services.application.audit import AuditService

_BACKUP_COUNT = 10
_BACKUP_LEN = 10
_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _hash_backup(code: str) -> str:
    return _pwd.hash(code)  # type: ignore[no-any-return]


def _verify_backup(code: str, hashed: str) -> bool:
    return _pwd.verify(code, hashed)  # type: ignore[no-any-return]


class TotpError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class TotpService:
    def __init__(self, repo: UserRepository, audit: AuditService | None = None) -> None:
        self._repo = repo
        self._audit = audit or AuditService()

    def generate_setup(self, user: User, issuer: str = "Qrew") -> tuple[str, str, list[str]]:
        """Generate a new TOTP secret, provisioning URI, and plaintext backup codes.

        Returns (secret, provisioning_uri, backup_codes_plaintext).
        The secret is NOT yet persisted — call confirm() to save it.
        """
        secret = pyotp.random_base32()
        totp = pyotp.TOTP(secret)
        uri = totp.provisioning_uri(name=user.email, issuer_name=issuer)
        backup_codes = [secrets.token_hex(_BACKUP_LEN // 2) for _ in range(_BACKUP_COUNT)]
        return secret, uri, backup_codes

    async def confirm(self, user: User, secret: str, code: str, backup_codes: list[str]) -> None:
        """Verify the first code against a pending secret and enable 2FA for the user."""
        totp = pyotp.TOTP(secret)
        if not totp.verify(code, valid_window=1):
            raise TotpError("Invalid code")
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

    async def verify_login(self, user: User, code: str) -> None:
        """Verify a TOTP code (or backup code) during the login challenge."""
        if not user.totp_enabled or user.totp_secret is None:
            raise TotpError("2FA not enabled")
        totp = pyotp.TOTP(user.totp_secret)
        if totp.verify(code, valid_window=1):
            await self._audit.record(
                action=AuditAction.TOTP_VERIFIED,
                actor_id=user.id,
                entity_type="user",
                entity_id=str(user.id),
            )
            return
        # Try backup codes
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
        await self._audit.record(
            action=AuditAction.TOTP_VERIFY_FAILED,
            actor_id=user.id,
            entity_type="user",
            entity_id=str(user.id),
        )
        raise TotpError("Invalid code")

    async def disable(self, user: User, code: str) -> None:
        """Verify the current TOTP code and then disable 2FA."""
        if not user.totp_enabled or user.totp_secret is None:
            raise TotpError("2FA is not enabled")
        totp = pyotp.TOTP(user.totp_secret)
        if not totp.verify(code, valid_window=1):
            raise TotpError("Invalid code")
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
