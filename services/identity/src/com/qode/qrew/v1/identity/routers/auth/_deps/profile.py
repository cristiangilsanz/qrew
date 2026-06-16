from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from com.qode.qrew.v1.identity.core.database import get_db
from com.qode.qrew.v1.identity.repositories.audit.audit import AuditRepository
from com.qode.qrew.v1.identity.repositories.passkey.passkey import (
    PasskeyCredentialRepository,
)
from com.qode.qrew.v1.identity.services.auth.profile import ProfileService


def get_profile_service(
    db: AsyncSession = Depends(get_db),
) -> ProfileService:
    """Build the profile service for the /me endpoints."""
    return ProfileService(
        passkey_repo=PasskeyCredentialRepository(db),
        audit_repo=AuditRepository(db),
    )
