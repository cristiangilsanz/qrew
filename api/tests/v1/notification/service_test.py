from unittest.mock import AsyncMock, MagicMock

import pytest

from com.qode.qrew.v1.service.models.notification import NotificationChannel
from com.qode.qrew.v1.service.services.notification import service as service_module
from com.qode.qrew.v1.service.services.notification.service import (
    NotificationService,
    _resolve_destination,  # pyright: ignore[reportPrivateUsage]
)


def _mock_user(
    email: str = "user@example.com", phone: str = "+34600000000"
) -> MagicMock:
    user = MagicMock()
    user.id = "00000000-0000-0000-0000-000000000001"
    user.email = email
    user.phone_number = phone
    return user


def test_resolve_destination_prefers_overrides() -> None:
    user = _mock_user()
    value = _resolve_destination(
        NotificationChannel.email,
        user,
        {NotificationChannel.email: "override@example.com"},
    )
    assert value == "override@example.com"


def test_resolve_destination_falls_back_to_user_email() -> None:
    user = _mock_user()
    assert _resolve_destination(NotificationChannel.email, user, None) == user.email


def test_resolve_destination_falls_back_to_user_phone() -> None:
    user = _mock_user()
    assert (
        _resolve_destination(NotificationChannel.sms, user, None) == user.phone_number
    )


def test_resolve_destination_requires_either_user_or_override() -> None:
    with pytest.raises(ValueError, match="no destination"):
        _resolve_destination(NotificationChannel.email, None, None)


async def test_service_persists_and_enqueues(monkeypatch: pytest.MonkeyPatch) -> None:
    inserted: list[object] = []

    class _FakeSessionContext:
        async def __aenter__(self) -> "_FakeSessionContext":
            return self

        async def __aexit__(self, *_: object) -> None:
            return None

        def begin(self) -> "_FakeSessionContext":
            return self

    class _FakeRepo:
        def __init__(self, *_: object) -> None:
            pass

        async def insert(self, row: object) -> object:
            inserted.append(row)
            return row

    monkeypatch.setattr(service_module, "AsyncSessionLocal", _FakeSessionContext)
    monkeypatch.setattr(service_module, "NotificationRepository", _FakeRepo)
    enqueue_mock = AsyncMock()
    monkeypatch.setattr(service_module, "enqueue", enqueue_mock)

    svc = NotificationService()
    user = _mock_user()
    ids = await svc.send(
        template_key="account_recovery",
        payload={"full_name": "Ada"},
        channels=[NotificationChannel.email],
        user=user,
    )
    assert len(ids) == 1
    assert len(inserted) == 1
    enqueue_mock.assert_awaited_once()
