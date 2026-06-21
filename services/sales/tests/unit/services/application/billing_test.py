import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from com.qode.qrew.v1.sales.models.reservation import ReservationStatus
from com.qode.qrew.v1.sales.services.application.billing import (
    PaymentContext,
    PaymentContextError,
    get_payment_context,
)
from conftest import make_inventory, make_reservation


def _make_db(
    *,
    reservation: object = None,
    inventory: object = None,
) -> MagicMock:
    from com.qode.qrew.v1.sales.repositories.projections import TicketTypeInventoryRepository
    from com.qode.qrew.v1.sales.repositories.reservation import ReservationRepository

    mock_reservation_repo = MagicMock(spec=ReservationRepository)
    mock_reservation_repo.get_by_id = AsyncMock(return_value=reservation)

    mock_inventory_repo = MagicMock(spec=TicketTypeInventoryRepository)
    mock_inventory_repo.get_by_id = AsyncMock(return_value=inventory)

    db = MagicMock()

    def _patch_repo(cls, session):  # type: ignore[no-untyped-def]
        pass

    import unittest.mock as mock

    mock.patch.object(ReservationRepository, "get_by_id", mock_reservation_repo.get_by_id).start()
    mock.patch.object(
        TicketTypeInventoryRepository, "get_by_id", mock_inventory_repo.get_by_id
    ).start()

    return db


async def _billing(
    *,
    user_id: uuid.UUID,
    reservation_id: uuid.UUID,
    reservation: object = None,
    inventory: object = None,
    currency: str = "EUR",
) -> PaymentContext:
    from unittest.mock import patch

    with (
        patch(
            "com.qode.qrew.v1.sales.services.application.billing.ReservationRepository"
        ) as MockRepo,
        patch(
            "com.qode.qrew.v1.sales.services.application.billing.TicketTypeInventoryRepository"
        ) as MockInv,
    ):
        MockRepo.return_value.get_by_id = AsyncMock(return_value=reservation)
        MockInv.return_value.get_by_id = AsyncMock(return_value=inventory)
        db = MagicMock()
        return await get_payment_context(
            db,
            reservation_id=reservation_id,
            user_id=user_id,
            default_currency=currency,
        )


class TestGetPaymentContext:
    async def test_raises_when_reservation_not_found(self, user_id: uuid.UUID) -> None:
        with pytest.raises(PaymentContextError) as exc_info:
            await _billing(user_id=user_id, reservation_id=uuid.uuid4(), reservation=None)
        assert exc_info.value.error_code == "not_found"

    async def test_raises_when_reservation_owned_by_other(
        self, user_id: uuid.UUID, event_id: uuid.UUID, ticket_type_id: uuid.UUID
    ) -> None:
        reservation = make_reservation(
            user_id=uuid.uuid4(), event_id=event_id, ticket_type_id=ticket_type_id
        )
        with pytest.raises(PaymentContextError) as exc_info:
            await _billing(user_id=user_id, reservation_id=reservation.id, reservation=reservation)
        assert exc_info.value.error_code == "not_found"

    async def test_raises_when_not_in_reserved_status(
        self, user_id: uuid.UUID, event_id: uuid.UUID, ticket_type_id: uuid.UUID
    ) -> None:
        for bad_status in (ReservationStatus.paid, ReservationStatus.cancelled):
            reservation = make_reservation(
                user_id=user_id,
                event_id=event_id,
                ticket_type_id=ticket_type_id,
                status=bad_status,
            )
            with pytest.raises(PaymentContextError) as exc_info:
                await _billing(
                    user_id=user_id, reservation_id=reservation.id, reservation=reservation
                )
            assert exc_info.value.error_code == "not_reserved"

    async def test_raises_when_reservation_expired(
        self, user_id: uuid.UUID, event_id: uuid.UUID, ticket_type_id: uuid.UUID
    ) -> None:
        reservation = make_reservation(
            user_id=user_id,
            event_id=event_id,
            ticket_type_id=ticket_type_id,
            expires_at=datetime.now(UTC) - timedelta(minutes=1),
        )
        with pytest.raises(PaymentContextError) as exc_info:
            await _billing(user_id=user_id, reservation_id=reservation.id, reservation=reservation)
        assert exc_info.value.error_code == "expired"

    async def test_raises_when_inventory_not_found(
        self, user_id: uuid.UUID, event_id: uuid.UUID, ticket_type_id: uuid.UUID
    ) -> None:
        reservation = make_reservation(
            user_id=user_id, event_id=event_id, ticket_type_id=ticket_type_id
        )
        with pytest.raises(PaymentContextError) as exc_info:
            await _billing(
                user_id=user_id,
                reservation_id=reservation.id,
                reservation=reservation,
                inventory=None,
            )
        assert exc_info.value.error_code == "not_found"

    async def test_happy_path_returns_correct_amount(
        self, user_id: uuid.UUID, event_id: uuid.UUID, ticket_type_id: uuid.UUID
    ) -> None:
        reservation = make_reservation(
            user_id=user_id,
            event_id=event_id,
            ticket_type_id=ticket_type_id,
            quantity=3,
        )
        inventory = make_inventory(
            ticket_type_id=ticket_type_id,
            event_id=event_id,
            price_cents=500,
            currency="GBP",
        )
        result = await _billing(
            user_id=user_id,
            reservation_id=reservation.id,
            reservation=reservation,
            inventory=inventory,
        )
        assert result.amount_cents == 1500
        assert result.currency == "GBP"

    async def test_falls_back_to_default_currency_when_inventory_has_none(
        self, user_id: uuid.UUID, event_id: uuid.UUID, ticket_type_id: uuid.UUID
    ) -> None:
        reservation = make_reservation(
            user_id=user_id,
            event_id=event_id,
            ticket_type_id=ticket_type_id,
            quantity=1,
        )
        inventory = make_inventory(
            ticket_type_id=ticket_type_id,
            event_id=event_id,
            price_cents=200,
            currency=None,  # type: ignore[arg-type]
        )
        result = await _billing(
            user_id=user_id,
            reservation_id=reservation.id,
            reservation=reservation,
            inventory=inventory,
            currency="USD",
        )
        assert result.currency == "USD"
