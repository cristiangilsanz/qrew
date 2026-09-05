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


# reads back the row the service left in the outbox
def _recorded(session: MagicMock) -> object:
    rows = [c.args[0] for c in session.add.call_args_list if hasattr(c.args[0], "subject")]
    assert rows, "no outbox row was recorded"
    return rows[-1]


# verifies that binding records the attested device
@pytest.mark.asyncio
async def test_binding_announces_the_attested_device() -> None:
    user_id = uuid.uuid4()
    device = _device(user_id)
    now = datetime.now(UTC)
    session = MagicMock()

    await _publish_device_attested(session, device, platform="android", attested_at=now)

    row = _recorded(session)
    assert row.subject == "identity.device.attested.v1"
    assert row.payload["device_id"] == str(device.id)
    assert row.payload["user_id"] == str(user_id)
    assert row.payload["attested_at"] == now.isoformat()
    assert row.payload["platform"] == "android"


# verifies that revocation announces the device
@pytest.mark.asyncio
async def test_revocation_announces_the_device() -> None:
    device_id, user_id = uuid.uuid4(), uuid.uuid4()
    revoked_at = datetime.now(UTC)
    session = MagicMock()

    await publish_device_revoked(session, device_id, user_id, revoked_at)

    row = _recorded(session)
    assert row.subject == "identity.device.revoked.v1"
    assert row.payload["device_id"] == str(device_id)
    assert row.payload["user_id"] == str(user_id)
    assert row.payload["revoked_at"] == revoked_at.isoformat()


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
    async def _capturar(session, device_id, user_id, revoked_at):  # type: ignore[no-untyped-def]
        del session
        publicados.append(device_id)

    with patch(f"{_MANAGEMENT}.publish_device_revoked", _capturar):
        count = await service.revoke_all_devices(user)

    assert count == 3
    assert publicados == revoked
