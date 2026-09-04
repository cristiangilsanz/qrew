# covers what binding does when the key it receives is already on record
import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from cryptography.hazmat.primitives.asymmetric import ec

from com.qode.qrew.v1.identity.services.application.authentication.device.binding import (
    DeviceBindingError,
    DeviceBindingService,
)
from conftest import make_user

_BINDING = "com.qode.qrew.v1.identity.services.application.authentication.device.binding"

_EC_KEY = ec.generate_private_key(ec.SECP256R1()).public_key()

_PUBLIC_KEY = "cHVibGljLWtleQ"
_SIGNATURE = "c2lnbmF0dXJl"


# builds a device already on record for a given owner
def _device(user_id: uuid.UUID, revoked: bool) -> MagicMock:
    device = MagicMock()
    device.id = uuid.uuid4()
    device.user_id = user_id
    device.revoked_at = datetime.now(UTC) if revoked else None
    return device


# builds the service with every collaborator stubbed out
def _service(existing: MagicMock | None) -> tuple[DeviceBindingService, MagicMock]:
    repo = MagicMock()
    repo.get_by_public_key = AsyncMock(return_value=existing)
    repo.save = AsyncMock(side_effect=lambda d: d)
    repo.create = AsyncMock(side_effect=lambda d: d)
    redis = MagicMock()
    redis.get = AsyncMock(return_value=b"challenge")
    redis.delete = AsyncMock()
    audit = MagicMock()
    audit.record = AsyncMock()
    return DeviceBindingService(repo, redis, audit), repo


# runs a completion with the signature checks and the attestation stubbed out
async def _complete(service: DeviceBindingService, user):
    with (
        patch(f"{_BINDING}.load_der_public_key", return_value=_EC_KEY),
        patch(f"{_BINDING}.verify_ecdsa"),
        patch(f"{_BINDING}.consume_attestation", AsyncMock(return_value="android")),
        patch(f"{_BINDING}._publish_device_attested", AsyncMock()),
    ):
        return await service.complete(user, "My Device", _PUBLIC_KEY, _SIGNATURE)


class TestBindingAKeyAlreadyOnRecord:
    # verifies that a key still bound to its owner is refused, since binding it
    # twice would leave two records for one device
    @pytest.mark.asyncio
    async def test_it_refuses_a_key_that_is_still_bound(self) -> None:
        user = make_user()
        service, _ = _service(_device(user.id, revoked=False))
        with pytest.raises(DeviceBindingError, match="already registered"):
            await _complete(service, user)

    # verifies that a key belonging to somebody else is refused
    @pytest.mark.asyncio
    async def test_it_refuses_a_key_that_belongs_to_another_account(self) -> None:
        user = make_user()
        service, _ = _service(_device(uuid.uuid4(), revoked=False))
        with pytest.raises(DeviceBindingError, match="already registered"):
            await _complete(service, user)

    # verifies that revoking a device does not lock its owner out of it, since the
    # key lives in the browser and arrives unchanged on every later binding
    @pytest.mark.asyncio
    async def test_it_revives_a_revoked_device_of_its_own_owner(self) -> None:
        user = make_user()
        existing = _device(user.id, revoked=True)
        service, repo = _service(existing)
        device = await _complete(service, user)
        assert device is existing
        assert existing.revoked_at is None
        assert existing.attested_at is not None
        repo.save.assert_awaited_once()
        repo.create.assert_not_awaited()

    # verifies that an unknown key still creates a record
    @pytest.mark.asyncio
    async def test_it_creates_a_record_for_an_unknown_key(self) -> None:
        user = make_user()
        service, repo = _service(None)
        await _complete(service, user)
        repo.create.assert_awaited_once()
        repo.save.assert_not_awaited()
