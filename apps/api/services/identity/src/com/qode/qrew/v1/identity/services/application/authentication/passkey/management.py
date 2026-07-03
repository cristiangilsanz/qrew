import uuid

import structlog

from com.qode.qrew.v1.identity.models.audit import AuditAction
from com.qode.qrew.v1.identity.repositories.passkey import (
    PasskeyCredentialRepository,
)
from com.qode.qrew.v1.identity.schemas.passkey import (
    PasskeyListResponse,
    PasskeyResponse,
)
from com.qode.qrew.v1.identity.services.application.audit import AuditService
from com.qode.qrew.v1.identity.services.application.authentication.passkey.assertion import (
    PasskeyError,
)

logger = structlog.get_logger(__name__)


class PasskeyManagementService:
    """List, rename, and delete the passkeys owned by a user."""

    def __init__(
        self,
        passkey_repo: PasskeyCredentialRepository,
        audit: AuditService,
    ) -> None:
        self._passkey_repo = passkey_repo
        self._audit = audit

    async def list_passkeys(self, user_id: uuid.UUID) -> PasskeyListResponse:
        """List all passkeys registered by the given user."""
        credentials = await self._passkey_repo.get_all_by_user_id(user_id)
        return PasskeyListResponse(
            passkeys=[
                PasskeyResponse(
                    id=str(c.id),
                    name=c.name,
                    aaguid=c.aaguid,
                    last_used_at=c.last_used_at,
                    created_at=c.created_at,
                )
                for c in credentials
            ]
        )

    async def delete_passkey(self, passkey_id: uuid.UUID, user_id: uuid.UUID) -> None:
        """Delete a passkey, refusing to remove the user's last one."""
        credential = await self._passkey_repo.get_by_id(passkey_id)
        if credential is None or credential.user_id != user_id:
            raise PasskeyError("Passkey not found", field="id")

        count = await self._passkey_repo.count_by_user_id(user_id)
        if count <= 1:
            raise PasskeyError(
                "Cannot delete the last passkey, register a new one first",
                field="id",
            )

        await self._passkey_repo.delete_by_id(passkey_id)
        await logger.ainfo("passkey_deleted", user_id=str(user_id), passkey_id=str(passkey_id))
        await self._audit_safe(AuditAction.PASSKEY_DELETED, user_id, passkey_id, payload=None)

    async def rename_passkey(
        self, passkey_id: uuid.UUID, user_id: uuid.UUID, name: str
    ) -> PasskeyResponse:
        """Rename a passkey and return the updated record."""
        credential = await self._passkey_repo.get_by_id(passkey_id)
        if credential is None or credential.user_id != user_id:
            raise PasskeyError("Passkey not found", field="id")

        credential.name = name
        updated = await self._passkey_repo.save(credential)
        await logger.ainfo("passkey_renamed", user_id=str(user_id), passkey_id=str(passkey_id))
        await self._audit_safe(
            AuditAction.PASSKEY_RENAMED,
            user_id,
            passkey_id,
            payload={"name": name},
        )
        return PasskeyResponse(
            id=str(updated.id),
            name=updated.name,
            aaguid=updated.aaguid,
            last_used_at=updated.last_used_at,
            created_at=updated.created_at,
        )

    async def _audit_safe(
        self,
        action: AuditAction,
        user_id: uuid.UUID,
        passkey_id: uuid.UUID,
        *,
        payload: dict[str, object] | None,
    ) -> None:
        """Record a management audit event without propagating errors."""
        try:
            await self._audit.record(
                action=action,
                actor_id=user_id,
                entity_type="passkey_credential",
                entity_id=str(passkey_id),
                payload=payload or {},
            )
        except Exception as exc:
            await logger.awarning("audit_write_failed", action=action, error=repr(exc))
