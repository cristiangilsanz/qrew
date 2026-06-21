import os

os.environ.setdefault("DEBUG", "true")

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from com.qode.qrew.v1.identity.models.user import KycStatus


@pytest.fixture
def user_id() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture
def actor_id() -> uuid.UUID:
    return uuid.uuid4()


def make_user(
    *,
    user_id: uuid.UUID | None = None,
    email: str = "user@example.com",
    full_name: str = "Test User",
    phone_number: str = "+31612345678",
    hashed_password: str = "hashed_pw",
    email_verified: bool = True,
    phone_number_verified: bool = True,
    kyc_status: KycStatus = KycStatus.approved,
    is_active: bool = True,
    is_admin: bool = False,
) -> SimpleNamespace:
    return SimpleNamespace(
        id=user_id or uuid.uuid4(),
        email=email,
        full_name=full_name,
        phone_number=phone_number,
        hashed_password=hashed_password,
        email_verified=email_verified,
        phone_number_verified=phone_number_verified,
        kyc_status=kyc_status,
        is_active=is_active,
        is_admin=is_admin,
        email_verification_token="tok123",
        email_verification_token_expires_at=None,
        phone_number_otp="123456",
        phone_number_otp_expires_at=None,
        created_at=None,
        deleted_at=None,
    )


def make_session(
    *,
    session_id: uuid.UUID | None = None,
    user_id: uuid.UUID | None = None,
    jti: str = "test-jti",
    device_fingerprint: str | None = None,
    device_id: uuid.UUID | None = None,
) -> SimpleNamespace:
    from datetime import UTC, datetime

    return SimpleNamespace(
        id=session_id or uuid.uuid4(),
        user_id=user_id or uuid.uuid4(),
        jti=jti,
        ip_address="1.2.3.4",
        user_agent="pytest",
        device_fingerprint=device_fingerprint,
        device_id=device_id,
        created_at=datetime.now(UTC),
        last_used_at=datetime.now(UTC),
    )


def make_audit_svc() -> AsyncMock:
    audit = AsyncMock()
    audit.record = AsyncMock()
    audit.get_recent_login_events = AsyncMock(return_value=[])
    return audit
