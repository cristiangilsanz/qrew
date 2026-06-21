from typing import Annotated

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from com.qode.qrew.v1.identity.core.utils import pii as pii_crypto
from com.qode.qrew.v1.identity.core.database import get_db
from com.qode.qrew.v1.identity.core.dependencies import get_redis
from com.qode.qrew.v1.identity.models.user import User

router = APIRouter(prefix="/dev", tags=["dev"])


class DevUserResponse(BaseModel):
    id: str
    email: str
    email_verified: bool
    phone_verified: bool
    is_admin: bool
    kyc_status: str
    email_verification_token: str | None
    phone_number_otp: str | None


@router.get("/user", response_model=DevUserResponse)
async def dev_get_user(
    email: str,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DevUserResponse:
    result = await db.execute(select(User).where(User.email_hash == pii_crypto.hash_lookup(email)))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return DevUserResponse(
        id=str(user.id),
        email=user.email,
        email_verified=user.email_verified,
        phone_verified=user.phone_number_verified,
        is_admin=user.is_admin,
        kyc_status=str(user.kyc_status),
        email_verification_token=user.email_verification_token,
        phone_number_otp=user.phone_number_otp,
    )


@router.post("/reset", status_code=204)
async def dev_reset_db(
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[aioredis.Redis, Depends(get_redis)],  # type: ignore[type-arg, assignment]
) -> None:
    await db.execute(
        text("TRUNCATE audit_events, sessions, passkey_credentials, users RESTART IDENTITY CASCADE")
    )
    await db.commit()
    await redis.flushdb()  # type: ignore[no-untyped-call]


@router.post("/make-admin", status_code=204)
async def dev_make_admin(
    email: str,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    result = await db.execute(select(User).where(User.email_hash == pii_crypto.hash_lookup(email)))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_admin = True
    await db.commit()
