import uuid
from unittest.mock import AsyncMock, MagicMock, patch


from com.qode.qrew.v1.sales.models.reservation import ReservationStatus
from com.qode.qrew.v1.sales.services.application.settlement import SettlementService
from conftest import make_inventory, make_reservation

_PATCH_REDLOCK = "com.qode.qrew.v1.sales.services.application.settlement.redlock"
_PATCH_SETTINGS = "com.qode.qrew.v1.sales.services.application.settlement.settings"
_PATCH_PUBLISH_PAID = "com.qode.qrew.v1.sales.services.application.settlement._publish_paid"
_PATCH_HOLDERS_REPO = (
    "com.qode.qrew.v1.sales.repositories.reservation_holder.ReservationHolderRepository"
)


def _make_svc(
    *,
    reservation: object = None,
    inventory: object = None,
) -> tuple[SettlementService, MagicMock]:
    """Build SettlementService replacing repos after construction to avoid real session.execute()."""
    session = MagicMock()
    session.commit = AsyncMock()
    svc = SettlementService(session)
    svc._reservations = MagicMock()
    svc._reservations.get_by_id = AsyncMock(return_value=reservation)
    svc._inventory = MagicMock()
    svc._inventory.get_by_id = AsyncMock(return_value=inventory)
    return svc, session


class TestSettlementMarkPaid:
    async def test_returns_none_when_reservation_not_found(self) -> None:
        svc, _ = _make_svc(reservation=None)
        with (
            patch(_PATCH_REDLOCK, return_value=_make_redlock()),
            patch(_PATCH_SETTINGS, _make_fake_settings()),
        ):
            result = await svc.mark_paid(uuid.uuid4())
        assert result is None

    async def test_returns_none_when_already_paid(
        self, user_id: uuid.UUID, event_id: uuid.UUID, ticket_type_id: uuid.UUID
    ) -> None:
        reservation = make_reservation(
            user_id=user_id,
            event_id=event_id,
            ticket_type_id=ticket_type_id,
            status=ReservationStatus.paid,
        )
        svc, _ = _make_svc(reservation=reservation)
        with (
            patch(_PATCH_REDLOCK, return_value=_make_redlock()),
            patch(_PATCH_SETTINGS, _make_fake_settings()),
        ):
            result = await svc.mark_paid(reservation.id)
        assert result is None

    async def test_returns_none_when_cancelled(
        self, user_id: uuid.UUID, event_id: uuid.UUID, ticket_type_id: uuid.UUID
    ) -> None:
        reservation = make_reservation(
            user_id=user_id,
            event_id=event_id,
            ticket_type_id=ticket_type_id,
            status=ReservationStatus.cancelled,
        )
        svc, _ = _make_svc(reservation=reservation)
        with (
            patch(_PATCH_REDLOCK, return_value=_make_redlock()),
            patch(_PATCH_SETTINGS, _make_fake_settings()),
        ):
            result = await svc.mark_paid(reservation.id)
        assert result is None

    async def test_marks_reservation_paid_and_commits(
        self, user_id: uuid.UUID, event_id: uuid.UUID, ticket_type_id: uuid.UUID
    ) -> None:
        reservation = make_reservation(
            user_id=user_id,
            event_id=event_id,
            ticket_type_id=ticket_type_id,
            status=ReservationStatus.reserved,
        )
        mock_holder_repo = MagicMock()
        mock_holder_repo.return_value.list_by_reservation = AsyncMock(return_value=[])
        svc, session = _make_svc(reservation=reservation)
        with (
            patch(_PATCH_REDLOCK, return_value=_make_redlock()),
            patch(_PATCH_SETTINGS, _make_fake_settings()),
            patch(_PATCH_PUBLISH_PAID, new=AsyncMock()),
            patch(_PATCH_HOLDERS_REPO, mock_holder_repo),
        ):
            result = await svc.mark_paid(reservation.id)
        assert result is reservation
        assert reservation.status == ReservationStatus.paid
        session.commit.assert_awaited_once()


class TestSettlementCancel:
    async def test_returns_none_when_not_found(self) -> None:
        svc, _ = _make_svc(reservation=None)
        with (
            patch(_PATCH_REDLOCK, return_value=_make_redlock()),
            patch(_PATCH_SETTINGS, _make_fake_settings()),
        ):
            result = await svc.cancel(uuid.uuid4(), reason="refund")
        assert result is None

    async def test_returns_none_when_already_cancelled(
        self, user_id: uuid.UUID, event_id: uuid.UUID, ticket_type_id: uuid.UUID
    ) -> None:
        reservation = make_reservation(
            user_id=user_id,
            event_id=event_id,
            ticket_type_id=ticket_type_id,
            status=ReservationStatus.cancelled,
        )
        svc, session = _make_svc(reservation=reservation)
        with (
            patch(_PATCH_REDLOCK, return_value=_make_redlock()),
            patch(_PATCH_SETTINGS, _make_fake_settings()),
        ):
            result = await svc.cancel(reservation.id, reason="refund")
        assert result is None
        session.commit.assert_not_awaited()

    async def test_returns_none_when_expired(
        self, user_id: uuid.UUID, event_id: uuid.UUID, ticket_type_id: uuid.UUID
    ) -> None:
        reservation = make_reservation(
            user_id=user_id,
            event_id=event_id,
            ticket_type_id=ticket_type_id,
            status=ReservationStatus.expired,
        )
        svc, session = _make_svc(reservation=reservation)
        with (
            patch(_PATCH_REDLOCK, return_value=_make_redlock()),
            patch(_PATCH_SETTINGS, _make_fake_settings()),
        ):
            result = await svc.cancel(reservation.id, reason="refund")
        assert result is None
        session.commit.assert_not_awaited()

    async def test_cancels_and_restores_inventory(
        self, user_id: uuid.UUID, event_id: uuid.UUID, ticket_type_id: uuid.UUID
    ) -> None:
        reservation = make_reservation(
            user_id=user_id,
            event_id=event_id,
            ticket_type_id=ticket_type_id,
            status=ReservationStatus.reserved,
            quantity=3,
        )
        inventory = make_inventory(
            ticket_type_id=ticket_type_id, event_id=event_id, reserved_count=10
        )
        svc, session = _make_svc(reservation=reservation, inventory=inventory)
        with (
            patch(_PATCH_REDLOCK, return_value=_make_redlock()),
            patch(_PATCH_SETTINGS, _make_fake_settings()),
        ):
            result = await svc.cancel(reservation.id, reason="refund")
        assert result is reservation
        assert reservation.status == ReservationStatus.cancelled
        assert inventory.reserved_count == 7
        session.commit.assert_awaited_once()

    async def test_inventory_count_never_goes_below_zero(
        self, user_id: uuid.UUID, event_id: uuid.UUID, ticket_type_id: uuid.UUID
    ) -> None:
        reservation = make_reservation(
            user_id=user_id,
            event_id=event_id,
            ticket_type_id=ticket_type_id,
            status=ReservationStatus.reserved,
            quantity=5,
        )
        inventory = make_inventory(
            ticket_type_id=ticket_type_id, event_id=event_id, reserved_count=3
        )
        svc, _ = _make_svc(reservation=reservation, inventory=inventory)
        with (
            patch(_PATCH_REDLOCK, return_value=_make_redlock()),
            patch(_PATCH_SETTINGS, _make_fake_settings()),
        ):
            await svc.cancel(reservation.id, reason="refund")
        assert inventory.reserved_count == 0

    async def test_cancel_without_inventory_still_cancels(
        self, user_id: uuid.UUID, event_id: uuid.UUID, ticket_type_id: uuid.UUID
    ) -> None:
        reservation = make_reservation(
            user_id=user_id,
            event_id=event_id,
            ticket_type_id=ticket_type_id,
            status=ReservationStatus.reserved,
        )
        svc, session = _make_svc(reservation=reservation, inventory=None)
        with (
            patch(_PATCH_REDLOCK, return_value=_make_redlock()),
            patch(_PATCH_SETTINGS, _make_fake_settings()),
        ):
            await svc.cancel(reservation.id, reason="refund")
        assert reservation.status == ReservationStatus.cancelled
        session.commit.assert_awaited_once()


def _make_redlock() -> MagicMock:
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=None)
    cm.__aexit__ = AsyncMock(return_value=None)
    return cm


def _make_fake_settings() -> MagicMock:
    s = MagicMock()
    s.redis_url = "redis://localhost:6379"
    return s
