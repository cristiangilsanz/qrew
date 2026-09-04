# tests publication
import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from com.qode.qrew.v1.identity.services.application.authentication.device.binding import (
    _publish_device_attested,
)
from com.qode.qrew.v1.identity.services.application.authentication.device.management import (
    DeviceService,
    publish_device_revoked,
)
from conftest import make_user

_BINDING = "com.qode.qrew.v1.identity.services.application.authentication.device.binding"
_MANAGEMENT = "com.qode.qrew.v1.identity.services.application.authentication.device.management"


# handles device
def _device(user_id: uuid.UUID) -> MagicMock:
    device = MagicMock()
    device.id = uuid.uuid4()
    device.user_id = user_id
    device.revoked_at = None
    return device


# verifies that binding announces the attested device
@pytest.mark.asyncio
async def test_binding_announces_the_attested_device() -> None:
    user_id = uuid.uuid4()
    device = _device(user_id)
    now = datetime.now(UTC)
    publish = AsyncMock()
    with patch("messaging.publisher.publish", publish):
        await _publish_device_attested(device, platform="android", attested_at=now)

    subject, envelope = publish.await_args.args
    assert subject == "identity.device.attested.v1"
    assert envelope.data["device_id"] == str(device.id)
    assert envelope.data["user_id"] == str(user_id)
    assert envelope.data["attested_at"] == now.isoformat()
    assert envelope.data["platform"] == "android"


# verifies that a failed publication does not break the binding
@pytest.mark.asyncio
async def test_a_failed_publication_does_not_break_the_binding() -> None:
    device = _device(uuid.uuid4())
    with patch("messaging.publisher.publish", AsyncMock(side_effect=RuntimeError("down"))):
        await _publish_device_attested(device, platform="ios", attested_at=datetime.now(UTC))


# verifies that revocation announces the device
@pytest.mark.asyncio
async def test_revocation_announces_the_device() -> None:
    device_id, user_id = uuid.uuid4(), uuid.uuid4()
    revoked_at = datetime.now(UTC)
    publish = AsyncMock()
    with patch("messaging.publisher.publish", publish):
        await publish_device_revoked(device_id, user_id, revoked_at)

    subject, envelope = publish.await_args.args
    assert subject == "identity.device.revoked.v1"
    assert envelope.data["device_id"] == str(device_id)
    assert envelope.data["user_id"] == str(user_id)
    assert envelope.data["revoked_at"] == revoked_at.isoformat()


# verifies that revoking every device announces each one
@pytest.mark.asyncio
async def test_revoking_every_device_announces_each_one() -> None:
    user = make_user()
    revoked = [uuid.uuid4(), uuid.uuid4(), uuid.uuid4()]
    repo = MagicMock()
    repo.revoke_all_by_user_id = AsyncMock(return_value=revoked)
    service = DeviceService(
        device_repo=repo,
        session_repo=MagicMock(),
        redis=MagicMock(),
        audit=MagicMock(record=AsyncMock()),
    )
    service._kill_all_sessions = AsyncMock()  # type: ignore[method-assign]

    publicados: list[uuid.UUID] = []

    # handles capturar
    async def _capturar(device_id, user_id, revoked_at):  # type: ignore[no-untyped-def]
        publicados.append(device_id)

    with patch(f"{_MANAGEMENT}.publish_device_revoked", _capturar):
        count = await service.revoke_all_devices(user)

    assert count == 3
    assert publicados == revoked
