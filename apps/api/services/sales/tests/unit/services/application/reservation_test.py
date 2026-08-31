# tests reservation
import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from com.qode.qrew.v1.sales.models.reservation import ReservationStatus
from com.qode.qrew.v1.sales.services.application.audit import AuditService
from com.qode.qrew.v1.sales.services.application.reservation import (
    FraudBlockedError,
    ReservationError,
    ReservationService,
)
from com.qode.qrew.v1.sales.services.domain.fraud.engine import FraudDecision, FraudEvaluation
from conftest import (
    make_event_ctx,
    make_inventory,
    make_reservation,
    make_reservation_item,
)

_PATCH_REDLOCK = "com.qode.qrew.v1.sales.services.application.reservation.redlock"
_PATCH_BUILD_ENGINE = (
    "com.qode.qrew.v1.sales.services.application.reservation.build_engine_for_user"
)
_PATCH_CONSUME_TOKEN = (
    "com.qode.qrew.v1.sales.services.application.reservation.consume_reservation_token"
)
_PATCH_SETTINGS = "com.qode.qrew.v1.sales.services.application.reservation.settings"


# handles make redlock
def _make_redlock() -> MagicMock:
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=None)
    cm.__aexit__ = AsyncMock(return_value=None)
    return cm


# handles make fake settings
def _make_fake_settings() -> MagicMock:
    s = MagicMock()
    s.redis_url = "redis://localhost:6379"
    s.reservation_ttl_seconds = 600
    return s


# handles allow
def _allow() -> FraudEvaluation:
    return FraudEvaluation(score=0, decision=FraudDecision.allow, signals=[])


# handles review
def _review() -> FraudEvaluation:
    return FraudEvaluation(score=50, decision=FraudDecision.review, signals=[])


# handles block
def _block() -> FraudEvaluation:
    return FraudEvaluation(score=90, decision=FraudDecision.block, signals=[])


# build a ReservationService with fully mocked dependencies
def _make_service(
    *,
    reservation: object = None,
    event_ctx: object = None,
    inventory: object = None,
    held: int = 0,
    items: list[object] | None = None,
) -> tuple[ReservationService, MagicMock]:
    session = MagicMock()
    session.get = AsyncMock(return_value=inventory)
    session.flush = AsyncMock()
    session.commit = AsyncMock()

    repo = MagicMock()
    repo.get_by_id = AsyncMock(return_value=reservation)
    repo.insert = AsyncMock(side_effect=lambda r: r)
    repo.active_quantity_for_user = AsyncMock(return_value=held)
    repo.list_items = AsyncMock(return_value=items if items is not None else [])

    event_ctx_repo = MagicMock()
    event_ctx_repo.get_by_event_id = AsyncMock(return_value=event_ctx)

    inventory_repo = MagicMock()

    audit = AsyncMock(spec=AuditService)
    audit.record = AsyncMock()

    svc = ReservationService(
        session=session,
        repo=repo,
        event_ctx_repo=event_ctx_repo,
        inventory_repo=inventory_repo,
        audit=audit,
    )
    return svc, session


class TestReservationServiceReserve:
    # verifies that raises when quantity less than one
    async def test_raises_when_quantity_less_than_one(
        self, user_id: uuid.UUID, event_id: uuid.UUID, ticket_type_id: uuid.UUID
    ) -> None:
        svc, _ = _make_service()
        engine = MagicMock()
        engine.evaluate = AsyncMock(return_value=_allow())
        with (
            patch(_PATCH_BUILD_ENGINE, new=AsyncMock(return_value=engine)),
            pytest.raises(ReservationError, match="Quantity"),
        ):
            await svc.reserve(
                user_id=user_id,
                event_id=event_id,
                items=[(ticket_type_id, 0)],
            )

    # verifies that raises when fraud blocked
    async def test_raises_when_fraud_blocked(
        self, user_id: uuid.UUID, event_id: uuid.UUID, ticket_type_id: uuid.UUID
    ) -> None:
        svc, _ = _make_service()
        engine = MagicMock()
        engine.evaluate = AsyncMock(return_value=_block())
        with (
            patch(_PATCH_BUILD_ENGINE, new=AsyncMock(return_value=engine)),
            patch(_PATCH_SETTINGS, _make_fake_settings()),
            pytest.raises(FraudBlockedError),
        ):
            await svc.reserve(
                user_id=user_id,
                event_id=event_id,
                items=[(ticket_type_id, 1)],
            )

    # verifies that raises when invalid reservation window token
    async def test_raises_when_invalid_reservation_window_token(
        self, user_id: uuid.UUID, event_id: uuid.UUID, ticket_type_id: uuid.UUID
    ) -> None:
        from jwt import InvalidTokenError

        svc, _ = _make_service()
        engine = MagicMock()
        engine.evaluate = AsyncMock(return_value=_allow())
        with (
            patch(_PATCH_BUILD_ENGINE, new=AsyncMock(return_value=engine)),
            patch(_PATCH_CONSUME_TOKEN, new=AsyncMock(side_effect=InvalidTokenError("bad"))),
            pytest.raises(ReservationError, match="invalid"),
        ):
            await svc.reserve(
                user_id=user_id,
                event_id=event_id,
                items=[(ticket_type_id, 1)],
                reservation_window_token="bad",
            )

    # verifies that raises when token for different event
    async def test_raises_when_token_for_different_event(
        self, user_id: uuid.UUID, event_id: uuid.UUID, ticket_type_id: uuid.UUID
    ) -> None:
        svc, _ = _make_service()
        engine = MagicMock()
        engine.evaluate = AsyncMock(return_value=_allow())
        with (
            patch(_PATCH_BUILD_ENGINE, new=AsyncMock(return_value=engine)),
            patch(_PATCH_CONSUME_TOKEN, new=AsyncMock(return_value=uuid.uuid4())),
            patch(_PATCH_REDLOCK, return_value=_make_redlock()),
            patch(_PATCH_SETTINGS, _make_fake_settings()),
            pytest.raises(ReservationError, match="different event"),
        ):
            await svc.reserve(
                user_id=user_id,
                event_id=event_id,
                items=[(ticket_type_id, 1)],
                reservation_window_token="tok",
            )

    # verifies that raises when event not found
    async def test_raises_when_event_not_found(
        self, user_id: uuid.UUID, event_id: uuid.UUID, ticket_type_id: uuid.UUID
    ) -> None:
        svc, _ = _make_service(event_ctx=None)
        engine = MagicMock()
        engine.evaluate = AsyncMock(return_value=_allow())
        with (
            patch(_PATCH_BUILD_ENGINE, new=AsyncMock(return_value=engine)),
            patch(_PATCH_REDLOCK, return_value=_make_redlock()),
            patch(_PATCH_SETTINGS, _make_fake_settings()),
            pytest.raises(ReservationError, match="Event not found."),
        ):
            await svc.reserve(
                user_id=user_id,
                event_id=event_id,
                items=[(ticket_type_id, 1)],
            )

    # verifies that raises when event not published
    async def test_raises_when_event_not_published(
        self, user_id: uuid.UUID, event_id: uuid.UUID, ticket_type_id: uuid.UUID
    ) -> None:
        ctx = make_event_ctx(event_id=event_id, status="draft")
        svc, _ = _make_service(event_ctx=ctx)
        engine = MagicMock()
        engine.evaluate = AsyncMock(return_value=_allow())
        with (
            patch(_PATCH_BUILD_ENGINE, new=AsyncMock(return_value=engine)),
            patch(_PATCH_REDLOCK, return_value=_make_redlock()),
            patch(_PATCH_SETTINGS, _make_fake_settings()),
            pytest.raises(ReservationError, match="not on sale"),
        ):
            await svc.reserve(
                user_id=user_id,
                event_id=event_id,
                items=[(ticket_type_id, 1)],
            )

    # verifies that raises when quantity exceeds per user max
    async def test_raises_when_quantity_exceeds_per_user_max(
        self, user_id: uuid.UUID, event_id: uuid.UUID, ticket_type_id: uuid.UUID
    ) -> None:
        ctx = make_event_ctx(event_id=event_id, max_tickets_per_user=2)
        svc, _ = _make_service(event_ctx=ctx)
        engine = MagicMock()
        engine.evaluate = AsyncMock(return_value=_allow())
        with (
            patch(_PATCH_BUILD_ENGINE, new=AsyncMock(return_value=engine)),
            patch(_PATCH_REDLOCK, return_value=_make_redlock()),
            patch(_PATCH_SETTINGS, _make_fake_settings()),
            pytest.raises(ReservationError, match="per-user maximum"),
        ):
            await svc.reserve(
                user_id=user_id,
                event_id=event_id,
                items=[(ticket_type_id, 5)],
            )

    # verifies that raises when sale window not configured
    async def test_raises_when_sale_window_not_configured(
        self, user_id: uuid.UUID, event_id: uuid.UUID, ticket_type_id: uuid.UUID
    ) -> None:
        ctx = make_event_ctx(event_id=event_id)
        ctx.sale_starts_at = None
        ctx.sale_ends_at = None
        svc, _ = _make_service(event_ctx=ctx)
        engine = MagicMock()
        engine.evaluate = AsyncMock(return_value=_allow())
        with (
            patch(_PATCH_BUILD_ENGINE, new=AsyncMock(return_value=engine)),
            patch(_PATCH_REDLOCK, return_value=_make_redlock()),
            patch(_PATCH_SETTINGS, _make_fake_settings()),
            pytest.raises(ReservationError, match="Sale window not configured."),
        ):
            await svc.reserve(
                user_id=user_id,
                event_id=event_id,
                items=[(ticket_type_id, 1)],
            )

    # verifies that raises when sale window closed
    async def test_raises_when_sale_window_closed(
        self, user_id: uuid.UUID, event_id: uuid.UUID, ticket_type_id: uuid.UUID
    ) -> None:
        now = datetime.now(UTC)
        ctx = make_event_ctx(
            event_id=event_id,
            sale_starts_at=now + timedelta(hours=1),
            sale_ends_at=now + timedelta(hours=2),
        )
        svc, _ = _make_service(event_ctx=ctx)
        engine = MagicMock()
        engine.evaluate = AsyncMock(return_value=_allow())
        with (
            patch(_PATCH_BUILD_ENGINE, new=AsyncMock(return_value=engine)),
            patch(_PATCH_REDLOCK, return_value=_make_redlock()),
            patch(_PATCH_SETTINGS, _make_fake_settings()),
            pytest.raises(ReservationError, match="Sale window closed."),
        ):
            await svc.reserve(
                user_id=user_id,
                event_id=event_id,
                items=[(ticket_type_id, 1)],
            )

    # verifies that raises when queue required and no token
    async def test_raises_when_queue_required_and_no_token(
        self, user_id: uuid.UUID, event_id: uuid.UUID, ticket_type_id: uuid.UUID
    ) -> None:
        ctx = make_event_ctx(event_id=event_id, queue_required=True)
        svc, _ = _make_service(event_ctx=ctx)
        engine = MagicMock()
        engine.evaluate = AsyncMock(return_value=_allow())
        with (
            patch(_PATCH_BUILD_ENGINE, new=AsyncMock(return_value=engine)),
            patch(_PATCH_REDLOCK, return_value=_make_redlock()),
            patch(_PATCH_SETTINGS, _make_fake_settings()),
            pytest.raises(ReservationError, match="token is required"),
        ):
            await svc.reserve(
                user_id=user_id,
                event_id=event_id,
                items=[(ticket_type_id, 1)],
                reservation_window_token=None,
            )

    # verifies that raises when no capacity
    async def test_raises_when_no_capacity(
        self, user_id: uuid.UUID, event_id: uuid.UUID, ticket_type_id: uuid.UUID
    ) -> None:
        ctx = make_event_ctx(event_id=event_id)
        inventory = make_inventory(
            ticket_type_id=ticket_type_id,
            event_id=event_id,
            capacity=5,
            reserved_count=4,
        )
        svc, _ = _make_service(event_ctx=ctx, inventory=inventory)
        engine = MagicMock()
        engine.evaluate = AsyncMock(return_value=_allow())
        with (
            patch(_PATCH_BUILD_ENGINE, new=AsyncMock(return_value=engine)),
            patch(_PATCH_REDLOCK, return_value=_make_redlock()),
            patch(_PATCH_SETTINGS, _make_fake_settings()),
            pytest.raises(ReservationError, match="Capacity exhausted"),
        ):
            await svc.reserve(
                user_id=user_id,
                event_id=event_id,
                items=[(ticket_type_id, 2)],
            )

    # verifies that raises when user held plus new exceeds limit
    async def test_raises_when_user_held_plus_new_exceeds_limit(
        self, user_id: uuid.UUID, event_id: uuid.UUID, ticket_type_id: uuid.UUID
    ) -> None:
        ctx = make_event_ctx(event_id=event_id, max_tickets_per_user=5)
        inventory = make_inventory(ticket_type_id=ticket_type_id, event_id=event_id, capacity=100)
        svc, _ = _make_service(event_ctx=ctx, inventory=inventory, held=4)
        engine = MagicMock()
        engine.evaluate = AsyncMock(return_value=_allow())
        with (
            patch(_PATCH_BUILD_ENGINE, new=AsyncMock(return_value=engine)),
            patch(_PATCH_REDLOCK, return_value=_make_redlock()),
            patch(_PATCH_SETTINGS, _make_fake_settings()),
            pytest.raises(ReservationError, match="Ticket limit exceeded"),
        ):
            await svc.reserve(
                user_id=user_id,
                event_id=event_id,
                items=[(ticket_type_id, 2)],
            )

    # verifies that happy path creates reservation
    async def test_happy_path_creates_reservation(
        self, user_id: uuid.UUID, event_id: uuid.UUID, ticket_type_id: uuid.UUID
    ) -> None:
        ctx = make_event_ctx(event_id=event_id)
        inventory = make_inventory(
            ticket_type_id=ticket_type_id, event_id=event_id, capacity=100, reserved_count=0
        )
        svc, session = _make_service(event_ctx=ctx, inventory=inventory)
        engine = MagicMock()
        engine.evaluate = AsyncMock(return_value=_allow())
        with (
            patch(_PATCH_BUILD_ENGINE, new=AsyncMock(return_value=engine)),
            patch(_PATCH_REDLOCK, return_value=_make_redlock()),
            patch(_PATCH_SETTINGS, _make_fake_settings()),
        ):
            result, _ = await svc.reserve(
                user_id=user_id,
                event_id=event_id,
                items=[(ticket_type_id, 2)],
            )
        assert result.user_id == user_id
        assert result.event_id == event_id
        assert result.quantity == 2
        assert result.status == ReservationStatus.reserved
        assert inventory.reserved_count == 2
        session.commit.assert_awaited()

    # verifies that review flag set when fraud review
    async def test_review_flag_set_when_fraud_review(
        self, user_id: uuid.UUID, event_id: uuid.UUID, ticket_type_id: uuid.UUID
    ) -> None:
        ctx = make_event_ctx(event_id=event_id)
        inventory = make_inventory(ticket_type_id=ticket_type_id, event_id=event_id, capacity=100)
        svc, _ = _make_service(event_ctx=ctx, inventory=inventory)
        engine = MagicMock()
        engine.evaluate = AsyncMock(return_value=_review())
        with (
            patch(_PATCH_BUILD_ENGINE, new=AsyncMock(return_value=engine)),
            patch(_PATCH_REDLOCK, return_value=_make_redlock()),
            patch(_PATCH_SETTINGS, _make_fake_settings()),
        ):
            result, _ = await svc.reserve(
                user_id=user_id,
                event_id=event_id,
                items=[(ticket_type_id, 1)],
            )
        assert result.requires_review is True
        assert result.risk_score == 50


class TestReservationServiceCancel:
    # verifies that raises when reservation not found
    async def test_raises_when_reservation_not_found(self, user_id: uuid.UUID) -> None:
        svc, _ = _make_service(reservation=None)
        with pytest.raises(ReservationError, match="not found"):
            await svc.cancel(actor_id=user_id, reservation_id=uuid.uuid4())

    # verifies that raises when owned by other
    async def test_raises_when_owned_by_other(
        self, user_id: uuid.UUID, event_id: uuid.UUID, ticket_type_id: uuid.UUID
    ) -> None:
        reservation = make_reservation(
            user_id=uuid.uuid4(), event_id=event_id, ticket_type_id=ticket_type_id
        )
        svc, _ = _make_service(reservation=reservation)
        with pytest.raises(ReservationError, match="not found"):
            await svc.cancel(actor_id=user_id, reservation_id=reservation.id)

    # verifies that returns early when already cancelled
    async def test_returns_early_when_already_cancelled(
        self, user_id: uuid.UUID, event_id: uuid.UUID, ticket_type_id: uuid.UUID
    ) -> None:
        reservation = make_reservation(
            user_id=user_id,
            event_id=event_id,
            ticket_type_id=ticket_type_id,
            status=ReservationStatus.cancelled,
        )
        svc, session = _make_service(reservation=reservation)
        result, _ = await svc.cancel(actor_id=user_id, reservation_id=reservation.id)
        assert result is reservation
        session.commit.assert_not_awaited()

    # verifies that returns early when expired
    async def test_returns_early_when_expired(
        self, user_id: uuid.UUID, event_id: uuid.UUID, ticket_type_id: uuid.UUID
    ) -> None:
        reservation = make_reservation(
            user_id=user_id,
            event_id=event_id,
            ticket_type_id=ticket_type_id,
            status=ReservationStatus.expired,
        )
        svc, session = _make_service(reservation=reservation)
        result, _ = await svc.cancel(actor_id=user_id, reservation_id=reservation.id)
        assert result is reservation
        session.commit.assert_not_awaited()

    # verifies that raises when paid
    async def test_raises_when_paid(
        self, user_id: uuid.UUID, event_id: uuid.UUID, ticket_type_id: uuid.UUID
    ) -> None:
        reservation = make_reservation(
            user_id=user_id,
            event_id=event_id,
            ticket_type_id=ticket_type_id,
            status=ReservationStatus.paid,
        )
        svc, _ = _make_service(reservation=reservation)
        with pytest.raises(ReservationError, match="refunded"):
            await svc.cancel(actor_id=user_id, reservation_id=reservation.id)

    # verifies that cancels and restores inventory
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
        svc, session = _make_service(
            reservation=reservation,
            inventory=inventory,
            items=[make_reservation_item(ticket_type_id=ticket_type_id, quantity=3)],
        )
        with (
            patch(_PATCH_REDLOCK, return_value=_make_redlock()),
            patch(_PATCH_SETTINGS, _make_fake_settings()),
        ):
            result, _ = await svc.cancel(actor_id=user_id, reservation_id=reservation.id)
        assert result.status == ReservationStatus.cancelled
        assert inventory.reserved_count == 7
        session.commit.assert_awaited()


class TestReservationServiceGetForUser:
    # verifies that raises when not found
    async def test_raises_when_not_found(self, user_id: uuid.UUID) -> None:
        svc, _ = _make_service(reservation=None)
        with pytest.raises(ReservationError, match="not found"):
            await svc.get_for_user(actor_id=user_id, reservation_id=uuid.uuid4())

    # verifies that raises when owned by other
    async def test_raises_when_owned_by_other(
        self, user_id: uuid.UUID, event_id: uuid.UUID, ticket_type_id: uuid.UUID
    ) -> None:
        reservation = make_reservation(
            user_id=uuid.uuid4(), event_id=event_id, ticket_type_id=ticket_type_id
        )
        svc, _ = _make_service(reservation=reservation)
        with pytest.raises(ReservationError, match="not found"):
            await svc.get_for_user(actor_id=user_id, reservation_id=reservation.id)

    # verifies that returns reservation for owner
    async def test_returns_reservation_for_owner(
        self, user_id: uuid.UUID, event_id: uuid.UUID, ticket_type_id: uuid.UUID
    ) -> None:
        reservation = make_reservation(
            user_id=user_id, event_id=event_id, ticket_type_id=ticket_type_id
        )
        svc, _ = _make_service(reservation=reservation)
        result, _ = await svc.get_for_user(actor_id=user_id, reservation_id=reservation.id)
        assert result is reservation
