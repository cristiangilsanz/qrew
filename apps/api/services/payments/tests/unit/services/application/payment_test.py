import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from com.qode.qrew.v1.payments.models.payment import PaymentStatus
from com.qode.qrew.v1.payments.services.application.payment import (
    PaymentError,
    PaymentExpiredError,
    PaymentService,
    WebhookError,
    _map_intent_status,
)
from conftest import make_payment

_PATCH_GET_CTX = "com.qode.qrew.v1.payments.services.application.payment._get_reservation_context"
_PATCH_CRYPTO = "com.qode.qrew.v1.payments.services.application.payment.pii_crypto"
_PATCH_CLAIM = "com.qode.qrew.v1.payments.services.infrastructure.webhooks.idempotency.claim_event"
_PATCH_DISPATCH = (
    "com.qode.qrew.v1.payments.services.infrastructure.webhooks.dispatch.dispatch_webhook_event"
)


def _make_ctx(
    *,
    is_valid: bool = True,
    amount_cents: int = 2000,
    currency: str = "EUR",
    error_code: str | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        is_valid=is_valid,
        amount_cents=amount_cents,
        currency=currency,
        error_code=error_code,
    )


def _make_intent(
    *, intent_id: str = "pi_test_123", client_secret: str = "secret_abc", status: str = "succeeded"
) -> SimpleNamespace:
    return SimpleNamespace(intent_id=intent_id, client_secret=client_secret, status=status)


def _make_svc(
    *,
    by_reservation: object = None,
    by_intent: object = None,
) -> tuple[PaymentService, MagicMock, MagicMock]:
    session = MagicMock()
    repo = MagicMock()
    repo.get_by_reservation_id = AsyncMock(return_value=by_reservation)
    repo.get_by_intent_id = AsyncMock(return_value=by_intent)
    repo.insert = AsyncMock(side_effect=lambda p: p)
    repo.flush = AsyncMock()
    stripe = AsyncMock()
    svc = PaymentService(session=session, repo=repo, stripe=stripe)
    return svc, repo, stripe


class TestMapIntentStatus:
    def test_succeeded(self) -> None:
        assert _map_intent_status("succeeded") == PaymentStatus.succeeded

    def test_processing(self) -> None:
        assert _map_intent_status("processing") == PaymentStatus.processing

    def test_requires_payment_method(self) -> None:
        assert _map_intent_status("requires_payment_method") == PaymentStatus.requires_action

    def test_requires_confirmation(self) -> None:
        assert _map_intent_status("requires_confirmation") == PaymentStatus.requires_action

    def test_canceled_maps_to_failed(self) -> None:
        assert _map_intent_status("canceled") == PaymentStatus.failed

    def test_unknown_maps_to_requires_action(self) -> None:
        assert _map_intent_status("unknown_status") == PaymentStatus.requires_action


class TestPaymentServiceInitiate:
    async def test_raises_expired_when_context_says_expired(
        self, user_id: uuid.UUID, reservation_id: uuid.UUID
    ) -> None:
        svc, _, _ = _make_svc()
        ctx = _make_ctx(is_valid=False, error_code="expired")
        with (
            patch(_PATCH_GET_CTX, new=AsyncMock(return_value=ctx)),
            pytest.raises(PaymentExpiredError),
        ):
            await svc.initiate(actor_id=user_id, reservation_id=reservation_id)

    async def test_raises_expired_on_410_code(
        self, user_id: uuid.UUID, reservation_id: uuid.UUID
    ) -> None:
        svc, _, _ = _make_svc()
        ctx = _make_ctx(is_valid=False, error_code="410")
        with (
            patch(_PATCH_GET_CTX, new=AsyncMock(return_value=ctx)),
            pytest.raises(PaymentExpiredError),
        ):
            await svc.initiate(actor_id=user_id, reservation_id=reservation_id)

    async def test_raises_not_found_when_404(
        self, user_id: uuid.UUID, reservation_id: uuid.UUID
    ) -> None:
        svc, _, _ = _make_svc()
        ctx = _make_ctx(is_valid=False, error_code="not_found")
        with (
            patch(_PATCH_GET_CTX, new=AsyncMock(return_value=ctx)),
            pytest.raises(PaymentError, match="not found"),
        ):
            await svc.initiate(actor_id=user_id, reservation_id=reservation_id)

    async def test_raises_generic_error_for_invalid_status(
        self, user_id: uuid.UUID, reservation_id: uuid.UUID
    ) -> None:
        svc, _, _ = _make_svc()
        ctx = _make_ctx(is_valid=False, error_code="not_reserved")
        with (
            patch(_PATCH_GET_CTX, new=AsyncMock(return_value=ctx)),
            pytest.raises(PaymentError, match="not pending"),
        ):
            await svc.initiate(actor_id=user_id, reservation_id=reservation_id)

    async def test_returns_existing_payment_when_intent_already_set(
        self, user_id: uuid.UUID, reservation_id: uuid.UUID
    ) -> None:
        existing = make_payment(reservation_id=reservation_id, intent_id="pi_existing")
        svc, repo, stripe = _make_svc(by_reservation=existing)
        ctx = _make_ctx()
        with patch(_PATCH_GET_CTX, new=AsyncMock(return_value=ctx)):
            result = await svc.initiate(actor_id=user_id, reservation_id=reservation_id)
        assert result is existing
        stripe.create_payment_intent.assert_not_awaited()
        repo.insert.assert_not_awaited()

    async def test_creates_new_payment_and_intent(
        self, user_id: uuid.UUID, reservation_id: uuid.UUID
    ) -> None:
        svc, repo, stripe = _make_svc(by_reservation=None)
        ctx = _make_ctx(amount_cents=3000, currency="GBP")
        intent = _make_intent(intent_id="pi_new", client_secret="secret_new", status="succeeded")
        stripe.create_payment_intent = AsyncMock(return_value=intent)
        mock_crypto = MagicMock()
        mock_crypto.encrypt = MagicMock(return_value=b"encrypted_secret")
        with (
            patch(_PATCH_GET_CTX, new=AsyncMock(return_value=ctx)),
            patch(_PATCH_CRYPTO, mock_crypto),
        ):
            result = await svc.initiate(actor_id=user_id, reservation_id=reservation_id)
        assert result.provider_payment_intent_id == "pi_new"
        assert result.status == PaymentStatus.succeeded
        assert result.client_secret_ciphertext == b"encrypted_secret"
        repo.insert.assert_awaited_once()

    async def test_updates_existing_payment_without_intent(
        self, user_id: uuid.UUID, reservation_id: uuid.UUID
    ) -> None:
        existing = make_payment(
            reservation_id=reservation_id, intent_id=None, client_secret_ciphertext=None
        )
        svc, repo, stripe = _make_svc(by_reservation=existing)
        ctx = _make_ctx()
        intent = _make_intent(intent_id="pi_attached", status="requires_action")
        stripe.create_payment_intent = AsyncMock(return_value=intent)
        mock_crypto = MagicMock()
        mock_crypto.encrypt = MagicMock(return_value=b"enc")
        with (
            patch(_PATCH_GET_CTX, new=AsyncMock(return_value=ctx)),
            patch(_PATCH_CRYPTO, mock_crypto),
        ):
            result = await svc.initiate(actor_id=user_id, reservation_id=reservation_id)
        assert result is existing
        assert existing.provider_payment_intent_id == "pi_attached"
        repo.insert.assert_not_awaited()
        repo.flush.assert_awaited_once()


class TestPaymentServiceDecryptClientSecret:
    def test_returns_none_when_ciphertext_is_none(
        self, user_id: uuid.UUID, reservation_id: uuid.UUID
    ) -> None:
        svc, _, _ = _make_svc()
        payment = make_payment(reservation_id=reservation_id, client_secret_ciphertext=None)
        mock_crypto = MagicMock()
        with patch(_PATCH_CRYPTO, mock_crypto):
            result = svc.decrypt_client_secret(payment)  # type: ignore[arg-type]
        assert result is None
        mock_crypto.decrypt.assert_not_called()

    def test_decrypts_ciphertext(self, user_id: uuid.UUID, reservation_id: uuid.UUID) -> None:
        svc, _, _ = _make_svc()
        payment = make_payment(reservation_id=reservation_id, client_secret_ciphertext=b"cipher")
        mock_crypto = MagicMock()
        mock_crypto.decrypt = MagicMock(return_value="the_secret")
        with patch(_PATCH_CRYPTO, mock_crypto):
            result = svc.decrypt_client_secret(payment)  # type: ignore[arg-type]
        assert result == "the_secret"
        mock_crypto.decrypt.assert_called_once_with(b"cipher")


class TestPaymentServiceApplySucceeded:
    async def test_silently_returns_when_not_found(self) -> None:
        svc, repo, _ = _make_svc(by_intent=None)
        await svc.apply_succeeded(intent_id="pi_unknown")
        repo.flush.assert_not_awaited()

    async def test_marks_succeeded_and_flushes(self, reservation_id: uuid.UUID) -> None:
        payment = make_payment(reservation_id=reservation_id, status=PaymentStatus.requires_action)
        svc, repo, _ = _make_svc(by_intent=payment)
        await svc.apply_succeeded(intent_id="pi_test")
        assert payment.status == PaymentStatus.succeeded
        repo.flush.assert_awaited_once()


class TestPaymentServiceApplyFailed:
    async def test_silently_returns_when_not_found(self) -> None:
        svc, repo, _ = _make_svc(by_intent=None)
        await svc.apply_failed(intent_id="pi_x", failure_code="card_declined", failure_message="No")
        repo.flush.assert_not_awaited()

    async def test_records_failure_and_flushes(self, reservation_id: uuid.UUID) -> None:
        payment = make_payment(reservation_id=reservation_id, status=PaymentStatus.processing)
        svc, repo, _ = _make_svc(by_intent=payment)
        await svc.apply_failed(
            intent_id="pi_test", failure_code="insufficient_funds", failure_message="Not enough"
        )
        assert payment.status == PaymentStatus.failed
        assert payment.failure_code == "insufficient_funds"
        assert payment.failure_message == "Not enough"
        repo.flush.assert_awaited_once()


class TestPaymentServiceApplyRefund:
    async def test_silently_returns_when_not_found(self) -> None:
        svc, repo, _ = _make_svc(by_intent=None)
        await svc.apply_refund(intent_id="pi_x", amount_refunded=1000, amount_total=2000)
        repo.flush.assert_not_awaited()

    async def test_partial_refund_does_not_change_status(self, reservation_id: uuid.UUID) -> None:
        payment = make_payment(reservation_id=reservation_id, status=PaymentStatus.succeeded)
        svc, repo, _ = _make_svc(by_intent=payment)
        await svc.apply_refund(intent_id="pi_test", amount_refunded=500, amount_total=2000)
        assert payment.status == PaymentStatus.succeeded
        repo.flush.assert_not_awaited()

    async def test_full_refund_sets_refunded_and_flushes(self, reservation_id: uuid.UUID) -> None:
        payment = make_payment(reservation_id=reservation_id, status=PaymentStatus.succeeded)
        svc, repo, _ = _make_svc(by_intent=payment)
        await svc.apply_refund(intent_id="pi_test", amount_refunded=2000, amount_total=2000)
        assert payment.status == PaymentStatus.refunded
        repo.flush.assert_awaited_once()

    async def test_overpaid_refund_counts_as_full(self, reservation_id: uuid.UUID) -> None:
        payment = make_payment(reservation_id=reservation_id, status=PaymentStatus.succeeded)
        svc, repo, _ = _make_svc(by_intent=payment)
        await svc.apply_refund(intent_id="pi_test", amount_refunded=2500, amount_total=2000)
        assert payment.status == PaymentStatus.refunded


class TestPaymentServiceApplyChargeback:
    async def test_silently_returns_when_not_found(self) -> None:
        svc, repo, _ = _make_svc(by_intent=None)
        await svc.apply_chargeback(intent_id="pi_x")
        repo.flush.assert_not_awaited()

    async def test_sets_refunded_and_flushes(self, reservation_id: uuid.UUID) -> None:
        payment = make_payment(reservation_id=reservation_id, status=PaymentStatus.succeeded)
        svc, repo, _ = _make_svc(by_intent=payment)
        await svc.apply_chargeback(intent_id="pi_test")
        assert payment.status == PaymentStatus.refunded
        repo.flush.assert_awaited_once()


class TestPaymentServiceRecordChargebackClosed:
    async def test_silently_returns_when_not_found(self) -> None:
        svc, repo, _ = _make_svc(by_intent=None)
        await svc.record_chargeback_closed(intent_id="pi_x")
        repo.flush.assert_not_awaited()

    async def test_publishes_event_without_status_change(self, reservation_id: uuid.UUID) -> None:
        payment = make_payment(reservation_id=reservation_id, status=PaymentStatus.refunded)
        svc, repo, _ = _make_svc(by_intent=payment)
        await svc.record_chargeback_closed(intent_id="pi_test")
        assert payment.status == PaymentStatus.refunded
        repo.flush.assert_not_awaited()


class TestPaymentServiceUpdateIntermediate:
    async def test_silently_returns_when_not_found(self) -> None:
        svc, repo, _ = _make_svc(by_intent=None)
        await svc.update_intermediate(intent_id="pi_x", status="processing")
        repo.flush.assert_not_awaited()

    async def test_skips_update_for_terminal_succeeded(self, reservation_id: uuid.UUID) -> None:
        payment = make_payment(reservation_id=reservation_id, status=PaymentStatus.processing)
        svc, repo, _ = _make_svc(by_intent=payment)
        await svc.update_intermediate(intent_id="pi_test", status="succeeded")
        assert payment.status == PaymentStatus.processing
        repo.flush.assert_not_awaited()

    async def test_skips_update_for_terminal_failed(self, reservation_id: uuid.UUID) -> None:
        payment = make_payment(reservation_id=reservation_id, status=PaymentStatus.processing)
        svc, repo, _ = _make_svc(by_intent=payment)
        await svc.update_intermediate(intent_id="pi_test", status="canceled")
        assert payment.status == PaymentStatus.processing
        repo.flush.assert_not_awaited()

    async def test_updates_intermediate_status(self, reservation_id: uuid.UUID) -> None:
        payment = make_payment(reservation_id=reservation_id, status=PaymentStatus.requires_action)
        svc, repo, _ = _make_svc(by_intent=payment)
        await svc.update_intermediate(intent_id="pi_test", status="processing")
        assert payment.status == PaymentStatus.processing
        repo.flush.assert_awaited_once()


class TestPaymentServiceHandleWebhook:
    async def test_raises_when_signature_missing(self) -> None:
        svc, _, _ = _make_svc()
        with pytest.raises(WebhookError, match="Stripe-Signature"):
            await svc.handle_webhook(b"payload", None)

    async def test_raises_when_signature_invalid(self) -> None:
        svc, _, stripe = _make_svc()
        stripe.verify_webhook = AsyncMock(side_effect=ValueError("bad sig"))
        with pytest.raises(WebhookError, match="Invalid Stripe signature"):
            await svc.handle_webhook(b"payload", "bad_sig")

    async def test_returns_duplicate_for_already_seen_event(self) -> None:
        svc, _, stripe = _make_svc()
        stripe.verify_webhook = AsyncMock(return_value={"id": "evt_123", "type": "x"})
        with patch(_PATCH_CLAIM, new=AsyncMock(return_value=False)):
            result = await svc.handle_webhook(b"payload", "sig_abc")
        assert result == {"status": "duplicate"}

    async def test_dispatches_and_returns_ok(self) -> None:
        svc, _, stripe = _make_svc()
        stripe.verify_webhook = AsyncMock(return_value={"id": "evt_456", "type": "x"})
        with (
            patch(_PATCH_CLAIM, new=AsyncMock(return_value=True)),
            patch(_PATCH_DISPATCH, new=AsyncMock(return_value=None)) as mock_dispatch,
        ):
            result = await svc.handle_webhook(b"payload", "sig_abc")
        assert result == {"status": "ok"}
        mock_dispatch.assert_awaited_once()

    async def test_raises_when_event_id_missing(self) -> None:
        svc, _, stripe = _make_svc()
        stripe.verify_webhook = AsyncMock(return_value={"type": "x"})
        with pytest.raises(WebhookError, match="missing id"):
            await svc.handle_webhook(b"payload", "sig_abc")
