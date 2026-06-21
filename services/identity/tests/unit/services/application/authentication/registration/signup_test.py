import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from com.qode.qrew.v1.identity.services.application.authentication.registration.signup import (
    RegistrationError,
    RegistrationService,
)
from com.qode.qrew.v1.identity.schemas.registration import RegisterRequest
from conftest import make_user

_MOD = "com.qode.qrew.v1.identity.services.application.authentication.registration.signup"
_PATCH_PWNED = f"{_MOD}.is_password_pwned"
_PATCH_BUILD_USER = f"{_MOD}._build_user"


def _make_request(
    *,
    email: str = "new@example.com",
    password: str = "StrongPass1!",
    phone: str = "+31612345678",
) -> RegisterRequest:
    return RegisterRequest.model_construct(
        full_name="Test User",
        email=email,
        phone_number=phone,
        password=password,
        terms_accepted=True,
        captcha_token="valid-token",
    )


def _make_svc(
    *,
    email_exists: bool = False,
    phone_exists: bool = False,
    captcha_raises: Exception | None = None,
) -> tuple[RegistrationService, MagicMock]:
    repo = MagicMock()
    repo.exists_by_email = AsyncMock(return_value=email_exists)
    repo.exists_by_phone = AsyncMock(return_value=phone_exists)
    created_user = make_user(user_id=uuid.uuid4())
    repo.create = AsyncMock(return_value=created_user)

    notifier = AsyncMock()
    notifier.send_email_verification_link = AsyncMock()
    notifier.send_sms_otp = AsyncMock()

    captcha = AsyncMock()
    if captcha_raises:
        captcha.verify = AsyncMock(side_effect=captcha_raises)
    else:
        captcha.verify = AsyncMock()

    audit = AsyncMock()
    audit.record = AsyncMock()

    svc = RegistrationService(repo=repo, notifier=notifier, captcha=captcha, audit=audit)
    return svc, repo


class TestRegistrationService:
    async def test_raises_when_captcha_invalid(self) -> None:
        svc, _ = _make_svc(captcha_raises=RegistrationError("Invalid captcha"))
        with (
            patch(_PATCH_PWNED, new=AsyncMock(return_value=False)),
            pytest.raises(RegistrationError, match="captcha"),
        ):
            await svc.register(_make_request(), ip_address="1.2.3.4")

    async def test_raises_when_email_taken(self) -> None:
        svc, _ = _make_svc(email_exists=True)
        with (
            patch(_PATCH_PWNED, new=AsyncMock(return_value=False)),
            pytest.raises(RegistrationError, match="Email already registered"),
        ):
            await svc.register(_make_request(), ip_address="1.2.3.4")

    async def test_raises_when_phone_taken(self) -> None:
        svc, _ = _make_svc(phone_exists=True)
        with (
            patch(_PATCH_PWNED, new=AsyncMock(return_value=False)),
            pytest.raises(RegistrationError, match="Phone number already registered"),
        ):
            await svc.register(_make_request(), ip_address="1.2.3.4")

    async def test_raises_when_password_breached(self) -> None:
        svc, _ = _make_svc()
        with (
            patch(_PATCH_PWNED, new=AsyncMock(return_value=True)),
            pytest.raises(RegistrationError, match="data breach"),
        ):
            await svc.register(_make_request(), ip_address="1.2.3.4")

    async def test_happy_path_creates_user(self) -> None:
        svc, repo = _make_svc()
        built = make_user()
        with (
            patch(_PATCH_PWNED, new=AsyncMock(return_value=False)),
            patch(_PATCH_BUILD_USER, return_value=built),
        ):
            response = await svc.register(_make_request(), ip_address="1.2.3.4")
        repo.create.assert_awaited_once()
        assert "Registration successful" in response.message

    async def test_sends_email_and_sms_notifications(self) -> None:
        svc, _ = _make_svc()
        built = make_user()
        with (
            patch(_PATCH_PWNED, new=AsyncMock(return_value=False)),
            patch(_PATCH_BUILD_USER, return_value=built),
        ):
            await svc.register(_make_request(), ip_address="1.2.3.4")
        svc._notifier.send_email_verification_link.assert_awaited_once()
        svc._notifier.send_sms_otp.assert_awaited_once()

    async def test_audit_failure_does_not_break_registration(self) -> None:
        svc, _ = _make_svc()
        svc._audit.record = AsyncMock(side_effect=RuntimeError("audit down"))
        built = make_user()
        with (
            patch(_PATCH_PWNED, new=AsyncMock(return_value=False)),
            patch(_PATCH_BUILD_USER, return_value=built),
        ):
            response = await svc.register(_make_request(), ip_address="1.2.3.4")
        assert response.message

    async def test_response_contains_user_id(self) -> None:
        svc, _ = _make_svc()
        built = make_user()
        with (
            patch(_PATCH_PWNED, new=AsyncMock(return_value=False)),
            patch(_PATCH_BUILD_USER, return_value=built),
        ):
            response = await svc.register(_make_request(), ip_address="1.2.3.4")
        assert response.id
        uuid.UUID(response.id)
