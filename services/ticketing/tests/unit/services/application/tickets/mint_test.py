import uuid
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest

from com.qode.qrew.v1.ticketing.services.application.audit import AuditService
from com.qode.qrew.v1.ticketing.services.application.tickets.mint import (
    MintedQr,
    _sample_audit,
    mint_qr,
    record_denial,
)
from conftest import make_gate_inputs

_PATCH_SIGN = "com.qode.qrew.v1.ticketing.services.application.tickets.mint.jwt_keys"
_PATCH_SETTINGS = "com.qode.qrew.v1.ticketing.services.application.tickets.mint.settings"


@pytest.fixture
def fake_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "com.qode.qrew.v1.ticketing.services.application.tickets.mint.settings",
        type(
            "S",
            (),
            {
                "ticket_qr_ttl_seconds": 20,
                "ticket_qr_audience": "qrew.scan",
                "ticket_qr_mint_audit_sample_rate": 1,
            },
        )(),
    )


class TestSampleAudit:
    def test_rate_one_always_true(self) -> None:
        assert all(_sample_audit(1) for _ in range(100))

    def test_rate_zero_always_true(self) -> None:
        assert all(_sample_audit(0) for _ in range(100))

    def test_large_rate_can_return_false(self) -> None:
        results = [_sample_audit(10_000) for _ in range(1000)]
        assert any(r is False for r in results)


class TestMintQr:
    async def test_returns_minted_qr(
        self,
        fake_settings: None,
        user_id: uuid.UUID,
        device_id: uuid.UUID,
        audit: AuditService,
        now: datetime,
    ) -> None:
        inputs = make_gate_inputs(user_id=user_id, device_id=device_id)

        with patch(_PATCH_SIGN) as mock_keys:
            mock_keys.sign.return_value = "signed.jwt.token"
            mock_keys.TICKET_QR = "ticket_qr"
            result = await mint_qr(
                inputs=inputs, user_id=user_id, device_id=device_id, audit=audit, now=now
            )

        assert isinstance(result, MintedQr)
        assert result.jwt == "signed.jwt.token"
        assert result.issued_at == now
        assert result.expires_at == now + timedelta(seconds=20)

    async def test_expires_at_uses_ttl_from_settings(
        self,
        fake_settings: None,
        user_id: uuid.UUID,
        device_id: uuid.UUID,
        audit: AuditService,
        now: datetime,
    ) -> None:
        inputs = make_gate_inputs(user_id=user_id, device_id=device_id)

        with patch(_PATCH_SIGN) as mock_keys:
            mock_keys.sign.return_value = "tok"
            mock_keys.TICKET_QR = "ticket_qr"
            result = await mint_qr(
                inputs=inputs, user_id=user_id, device_id=device_id, audit=audit, now=now
            )

        assert result.expires_at - result.issued_at == timedelta(seconds=20)

    async def test_binds_device_when_different(
        self,
        fake_settings: None,
        user_id: uuid.UUID,
        device_id: uuid.UUID,
        audit: AuditService,
        now: datetime,
    ) -> None:
        other_device = uuid.uuid4()
        inputs = make_gate_inputs(
            user_id=user_id, device_id=device_id, bound_device_id=other_device
        )
        assert inputs.ticket.bound_device_id == other_device

        with patch(_PATCH_SIGN) as mock_keys:
            mock_keys.sign.return_value = "tok"
            mock_keys.TICKET_QR = "ticket_qr"
            await mint_qr(inputs=inputs, user_id=user_id, device_id=device_id, audit=audit, now=now)

        assert inputs.ticket.bound_device_id == device_id

    async def test_does_not_rebind_when_already_bound(
        self,
        fake_settings: None,
        user_id: uuid.UUID,
        device_id: uuid.UUID,
        audit: AuditService,
        now: datetime,
    ) -> None:
        inputs = make_gate_inputs(user_id=user_id, device_id=device_id, bound_device_id=device_id)

        with patch(_PATCH_SIGN) as mock_keys:
            mock_keys.sign.return_value = "tok"
            mock_keys.TICKET_QR = "ticket_qr"
            await mint_qr(inputs=inputs, user_id=user_id, device_id=device_id, audit=audit, now=now)

        assert inputs.ticket.bound_device_id == device_id

    async def test_audit_recorded_when_sample_rate_1(
        self,
        fake_settings: None,
        user_id: uuid.UUID,
        device_id: uuid.UUID,
        audit: AuditService,
        now: datetime,
    ) -> None:
        inputs = make_gate_inputs(user_id=user_id, device_id=device_id)

        with patch(_PATCH_SIGN) as mock_keys:
            mock_keys.sign.return_value = "tok"
            mock_keys.TICKET_QR = "ticket_qr"
            await mint_qr(inputs=inputs, user_id=user_id, device_id=device_id, audit=audit, now=now)

        audit.record.assert_awaited_once()  # type: ignore[attr-defined]

    async def test_audit_failure_does_not_raise(
        self,
        fake_settings: None,
        user_id: uuid.UUID,
        device_id: uuid.UUID,
        now: datetime,
    ) -> None:
        broken_audit = AsyncMock(spec=AuditService)
        broken_audit.record = AsyncMock(side_effect=RuntimeError("audit down"))
        inputs = make_gate_inputs(user_id=user_id, device_id=device_id)

        with patch(_PATCH_SIGN) as mock_keys:
            mock_keys.sign.return_value = "tok"
            mock_keys.TICKET_QR = "ticket_qr"
            result = await mint_qr(
                inputs=inputs,
                user_id=user_id,
                device_id=device_id,
                audit=broken_audit,
                now=now,
            )

        assert isinstance(result, MintedQr)


class TestRecordDenial:
    async def test_records_denial_with_device(
        self,
        user_id: uuid.UUID,
        device_id: uuid.UUID,
        audit: AuditService,
    ) -> None:
        ticket_id = uuid.uuid4()
        await record_denial(
            audit=audit,
            user_id=user_id,
            ticket_id=ticket_id,
            reason="state",
            device_id=device_id,
        )
        audit.record.assert_awaited_once()  # type: ignore[attr-defined]
        call_kwargs = audit.record.call_args.kwargs  # type: ignore[attr-defined]
        assert call_kwargs["payload"]["reason"] == "state"
        assert call_kwargs["payload"]["device_id"] == str(device_id)

    async def test_records_denial_without_device(
        self,
        user_id: uuid.UUID,
        audit: AuditService,
    ) -> None:
        await record_denial(
            audit=audit,
            user_id=user_id,
            ticket_id=uuid.uuid4(),
            reason="reassertion",
            device_id=None,
        )
        call_kwargs = audit.record.call_args.kwargs  # type: ignore[attr-defined]
        assert call_kwargs["payload"]["device_id"] is None

    async def test_audit_failure_does_not_raise(
        self,
        user_id: uuid.UUID,
        device_id: uuid.UUID,
    ) -> None:
        broken_audit = AsyncMock(spec=AuditService)
        broken_audit.record = AsyncMock(side_effect=RuntimeError("down"))
        await record_denial(
            audit=broken_audit,
            user_id=user_id,
            ticket_id=uuid.uuid4(),
            reason="state",
            device_id=device_id,
        )
