import uuid
from unittest.mock import AsyncMock, patch

import httpx
import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from com.qode.qrew.v1.payments.services.application.payment import _ReservationContext

pytestmark = [pytest.mark.integration, pytest.mark.asyncio(loop_scope="session")]


@pytest_asyncio.fixture(autouse=True)
async def clean_payments(test_session_factory: async_sessionmaker[AsyncSession]) -> None:
    async with test_session_factory() as session, session.begin():
        await session.execute(text("TRUNCATE payments.payments RESTART IDENTITY CASCADE"))


_PAYMENT_URL = "/v1/reservations/{}/payment"
_WEBHOOK_URL = "/v1/payments/webhook"

_VALID_CTX = _ReservationContext(amount_cents=2000, currency="EUR", is_valid=True)


def _patch_sales(ctx: _ReservationContext):
    return patch(
        "com.qode.qrew.v1.payments.services.application.payment._get_reservation_context",
        return_value=ctx,
    )


@pytest.mark.integration
async def test_initiate_payment_success(
    client: httpx.AsyncClient,
    auth_headers: tuple[uuid.UUID, dict[str, str]],
    mock_stripe: AsyncMock,
) -> None:
    user_id, headers = auth_headers
    reservation_id = uuid.uuid4()

    with _patch_sales(_VALID_CTX):
        resp = await client.post(_PAYMENT_URL.format(reservation_id), headers=headers)

    assert resp.status_code == 201
    body = resp.json()
    assert body["reservation_id"] == str(reservation_id)
    assert body["amount_cents"] == 2000
    assert body["currency"] == "EUR"
    assert body["client_secret"] == "pi_test_123_secret_abc"
    assert body["status"] == "requires_action"
    mock_stripe.create_payment_intent.assert_called_once()


@pytest.mark.integration
async def test_initiate_payment_no_auth(client: httpx.AsyncClient) -> None:
    reservation_id = uuid.uuid4()
    resp = await client.post(_PAYMENT_URL.format(reservation_id))
    assert resp.status_code in (401, 403)


@pytest.mark.integration
async def test_initiate_payment_reservation_not_found(
    client: httpx.AsyncClient,
    auth_headers: tuple[uuid.UUID, dict[str, str]],
    mock_stripe: AsyncMock,
) -> None:
    user_id, headers = auth_headers
    reservation_id = uuid.uuid4()
    ctx = _ReservationContext(amount_cents=0, currency="", is_valid=False, error_code="not_found")

    with _patch_sales(ctx):
        resp = await client.post(_PAYMENT_URL.format(reservation_id), headers=headers)

    assert resp.status_code == 404
    mock_stripe.create_payment_intent.assert_not_called()


@pytest.mark.integration
async def test_initiate_payment_expired(
    client: httpx.AsyncClient,
    auth_headers: tuple[uuid.UUID, dict[str, str]],
    mock_stripe: AsyncMock,
) -> None:
    user_id, headers = auth_headers
    reservation_id = uuid.uuid4()
    ctx = _ReservationContext(amount_cents=0, currency="", is_valid=False, error_code="expired")

    with _patch_sales(ctx):
        resp = await client.post(_PAYMENT_URL.format(reservation_id), headers=headers)

    assert resp.status_code == 410
    mock_stripe.create_payment_intent.assert_not_called()


@pytest.mark.integration
async def test_initiate_payment_idempotent(
    client: httpx.AsyncClient,
    auth_headers: tuple[uuid.UUID, dict[str, str]],
    mock_stripe: AsyncMock,
) -> None:
    user_id, headers = auth_headers
    reservation_id = uuid.uuid4()

    with _patch_sales(_VALID_CTX):
        resp1 = await client.post(_PAYMENT_URL.format(reservation_id), headers=headers)
        resp2 = await client.post(_PAYMENT_URL.format(reservation_id), headers=headers)

    assert resp1.status_code == 201
    assert resp2.status_code == 201
    assert resp1.json()["id"] == resp2.json()["id"]
    mock_stripe.create_payment_intent.assert_called_once()


@pytest.mark.integration
async def test_webhook_missing_signature(client: httpx.AsyncClient) -> None:
    resp = await client.post(_WEBHOOK_URL, content=b'{"id":"evt_1"}')
    assert resp.status_code == 400


@pytest.mark.integration
async def test_webhook_success_event(
    client: httpx.AsyncClient,
    mock_stripe: AsyncMock,
) -> None:
    event_id = f"evt_{uuid.uuid4().hex[:12]}"
    mock_stripe.verify_webhook.return_value = {
        "id": event_id,
        "type": "payment_intent.succeeded",
        "data": {"object": {"id": "pi_test_123"}},
    }

    resp = await client.post(
        _WEBHOOK_URL,
        content=b'{"id":"evt_1"}',
        headers={"Stripe-Signature": "t=1,v1=abc"},
    )

    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
    mock_stripe.verify_webhook.assert_called_once()


@pytest.mark.integration
async def test_webhook_refund_event(
    client: httpx.AsyncClient,
    mock_stripe: AsyncMock,
) -> None:
    event_id = f"evt_{uuid.uuid4().hex[:12]}"
    mock_stripe.verify_webhook.return_value = {
        "id": event_id,
        "type": "charge.refunded",
        "data": {
            "object": {
                "payment_intent": "pi_test_123",
                "amount": 2000,
                "amount_refunded": 2000,
            }
        },
    }

    resp = await client.post(
        _WEBHOOK_URL,
        content=b'{"id":"evt_1"}',
        headers={"Stripe-Signature": "t=1,v1=abc"},
    )

    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
