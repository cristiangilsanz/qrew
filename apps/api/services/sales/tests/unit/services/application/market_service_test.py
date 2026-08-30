# tests the market service rules for queues assignments and their payment context
import uuid
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from com.qode.qrew.v1.sales.models.market import MarketAssignmentState, MarketListingState
from com.qode.qrew.v1.sales.services.application.market.service import (
    MarketError,
    MarketService,
)

pytestmark = pytest.mark.asyncio

FUTURE = datetime.now(UTC) + timedelta(hours=1)
PAST = datetime.now(UTC) - timedelta(hours=1)


# builds a market service whose repositories are all stand ins
def _make_service(
    *,
    assignment: object = None,
    listing: object = None,
    event_ctx: object = None,
    queue_entry: object = None,
    active_tickets: int = 0,
) -> tuple[MarketService, MagicMock]:
    repo = MagicMock()
    repo.get_assignment_by_id = AsyncMock(return_value=assignment)
    repo.get_listing_by_id = AsyncMock(return_value=listing)
    repo.get_queue_entry = AsyncMock(return_value=queue_entry)
    repo.active_ticket_count_for_user = AsyncMock(return_value=active_tickets)
    repo.insert_queue_entry = AsyncMock(side_effect=lambda e: e)
    repo.flush = AsyncMock()
    repo.get_pending_assignment_for_user = AsyncMock(return_value=None)
    repo.get_pending_assignment_for_user_any_event = AsyncMock(return_value=assignment)
    repo.list_recent_assignments_for_user = AsyncMock(return_value=[])
    repo.active_queue_count = AsyncMock(return_value=3)
    repo.get_active_queue_entries_for_user = AsyncMock(return_value=[])

    event_ctx_repo = MagicMock()
    event_ctx_repo.get_by_event_id = AsyncMock(return_value=event_ctx)

    audit = MagicMock()
    audit.record = AsyncMock()

    service = MarketService(
        repo,
        event_ctx_repo,
        MagicMock(),
        audit,
        assignment_ttl_hours=3,
        listing_ttl_days=7,
    )
    return service, repo


# builds a stand in assignment row
def _assignment(**kwargs: object) -> SimpleNamespace:
    base = {
        "id": uuid.uuid4(),
        "listing_id": uuid.uuid4(),
        "event_id": uuid.uuid4(),
        "buyer_user_id": uuid.uuid4(),
        "state": MarketAssignmentState.pending,
        "expires_at": FUTURE,
        "holder_name": "Admin",
        "holder_dni": "00000001R",
        "holder_document_type": "dni",
        "payment_intent_id": None,
    }
    base.update(kwargs)
    return SimpleNamespace(**base)


# builds a stand in event context row
def _event_ctx(**kwargs: object) -> SimpleNamespace:
    base = {
        "status": "published",
        "sale_ends_at": PAST,
        "max_tickets_per_user": 4,
    }
    base.update(kwargs)
    return SimpleNamespace(**base)


class TestJoinQueue:
    # verifies that an unknown event cannot be queued for
    async def test_rejects_an_unknown_event(self) -> None:
        service, _ = _make_service(event_ctx=None)
        with pytest.raises(MarketError, match="Event not found"):
            await service.join_queue(user_id=uuid.uuid4(), event_id=uuid.uuid4())

    # verifies that the queue stays closed while the sale is still running
    async def test_rejects_while_the_sale_is_open(self) -> None:
        service, _ = _make_service(event_ctx=_event_ctx(sale_ends_at=FUTURE))
        with pytest.raises(MarketError, match="sale window has closed"):
            await service.join_queue(user_id=uuid.uuid4(), event_id=uuid.uuid4())

    # verifies that a user already at the ticket limit cannot queue for more
    async def test_rejects_a_user_at_the_ticket_limit(self) -> None:
        service, _ = _make_service(event_ctx=_event_ctx(), active_tickets=4)
        with pytest.raises(MarketError, match="maximum number of tickets"):
            await service.join_queue(user_id=uuid.uuid4(), event_id=uuid.uuid4())

    # verifies that joining twice returns the place already held
    async def test_returns_the_existing_entry(self) -> None:
        existing = SimpleNamespace(id=uuid.uuid4())
        service, repo = _make_service(event_ctx=_event_ctx(), queue_entry=existing)
        result = await service.join_queue(user_id=uuid.uuid4(), event_id=uuid.uuid4())
        assert result is existing
        repo.insert_queue_entry.assert_not_awaited()

    # verifies that a first join creates the entry
    async def test_creates_an_entry(self) -> None:
        service, repo = _make_service(event_ctx=_event_ctx())
        result = await service.join_queue(user_id=uuid.uuid4(), event_id=uuid.uuid4())
        assert result is not None
        repo.insert_queue_entry.assert_awaited_once()


class TestLeaveQueue:
    # verifies that leaving without a place reports nothing happened
    async def test_reports_false_without_an_entry(self) -> None:
        service, _ = _make_service(queue_entry=None)
        assert await service.leave_queue(user_id=uuid.uuid4(), event_id=uuid.uuid4()) is False

    # verifies that leaving stamps the entry
    async def test_stamps_the_entry(self) -> None:
        entry = SimpleNamespace(left_at=None)
        service, _ = _make_service(queue_entry=entry)
        assert await service.leave_queue(user_id=uuid.uuid4(), event_id=uuid.uuid4()) is True
        assert entry.left_at is not None


class TestQueueStatus:
    # verifies that the standing reports the place and the queue size
    async def test_reports_the_standing(self) -> None:
        entry = SimpleNamespace(joined_at=PAST)
        service, _ = _make_service(queue_entry=entry)
        status = await service.queue_status(user_id=uuid.uuid4(), event_id=uuid.uuid4())
        assert status["in_queue"] is True
        assert status["queue_count"] == 3
        assert status["pending_assignment_id"] is None


class TestSetHolders:
    # verifies that another user's assignment cannot be named
    async def test_rejects_an_assignment_owned_by_someone_else(self) -> None:
        service, _ = _make_service(assignment=_assignment())
        with pytest.raises(MarketError, match="Assignment not found"):
            await service.set_holders(
                user_id=uuid.uuid4(),
                assignment_id=uuid.uuid4(),
                holder_name="A",
                holder_document_type="dni",
                holder_dni="00000001R",
            )

    # verifies that a closed assignment can no longer be named
    async def test_rejects_a_closed_assignment(self) -> None:
        assignment = _assignment(state=MarketAssignmentState.paid)
        service, _ = _make_service(assignment=assignment)
        with pytest.raises(MarketError, match="already closed"):
            await service.set_holders(
                user_id=assignment.buyer_user_id,
                assignment_id=assignment.id,
                holder_name="A",
                holder_document_type="dni",
                holder_dni="00000001R",
            )

    # verifies that an expired assignment can no longer be named
    async def test_rejects_an_expired_assignment(self) -> None:
        assignment = _assignment(expires_at=PAST)
        service, _ = _make_service(assignment=assignment)
        with pytest.raises(MarketError, match="expired"):
            await service.set_holders(
                user_id=assignment.buyer_user_id,
                assignment_id=assignment.id,
                holder_name="A",
                holder_document_type="dni",
                holder_dni="00000001R",
            )

    # verifies that the holder and the document type are both stored
    async def test_stores_the_holder_and_its_document_type(self) -> None:
        assignment = _assignment(holder_name=None, holder_dni=None, holder_document_type=None)
        service, _ = _make_service(assignment=assignment)
        result = await service.set_holders(
            user_id=assignment.buyer_user_id,
            assignment_id=assignment.id,
            holder_name="Foreign Guest",
            holder_document_type="other",
            holder_dni="AB123456",
        )
        assert result.holder_name == "Foreign Guest"
        assert result.holder_document_type == "other"
        assert result.holder_dni == "AB123456"


class TestGetPaymentContext:
    # verifies that an assignment cannot be charged before its holder is named
    async def test_rejects_when_no_holder_is_named(self) -> None:
        assignment = _assignment(holder_name=None, holder_dni=None)
        service, _ = _make_service(assignment=assignment)
        with pytest.raises(MarketError, match="Holders not set"):
            await service.get_payment_context(
                user_id=assignment.buyer_user_id, assignment_id=assignment.id
            )

    # verifies that an assignment that is not pending cannot be charged
    async def test_rejects_when_not_pending(self) -> None:
        assignment = _assignment(state=MarketAssignmentState.expired)
        service, _ = _make_service(assignment=assignment)
        with pytest.raises(MarketError, match="not pending payment"):
            await service.get_payment_context(
                user_id=assignment.buyer_user_id, assignment_id=assignment.id
            )

    # verifies that a missing listing leaves nothing to charge for
    async def test_rejects_without_a_listing(self) -> None:
        assignment = _assignment()
        service, _ = _make_service(assignment=assignment, listing=None)
        with pytest.raises(MarketError, match="Listing not found"):
            await service.get_payment_context(
                user_id=assignment.buyer_user_id, assignment_id=assignment.id
            )

    # verifies that the price comes from the listing
    async def test_prices_from_the_listing(self) -> None:
        assignment = _assignment()
        listing = SimpleNamespace(price_cents=7500, currency="EUR")
        service, _ = _make_service(assignment=assignment, listing=listing)
        context = await service.get_payment_context(
            user_id=assignment.buyer_user_id, assignment_id=assignment.id
        )
        assert context == {"amount_cents": 7500, "currency": "EUR"}


class TestRecordPaymentIntent:
    # verifies that the intent is stored against the assignment
    async def test_stores_the_intent(self) -> None:
        assignment = _assignment()
        service, _ = _make_service(assignment=assignment)
        await service.record_payment_intent(
            user_id=assignment.buyer_user_id,
            assignment_id=assignment.id,
            payment_intent_id="pi_1",
        )
        assert assignment.payment_intent_id == "pi_1"


class TestDeclineAssignment:
    # verifies that only a pending assignment can be declined
    async def test_rejects_a_closed_assignment(self) -> None:
        assignment = _assignment(state=MarketAssignmentState.paid)
        service, _ = _make_service(assignment=assignment)
        with pytest.raises(MarketError, match="not declined"):
            await service.decline_assignment(
                user_id=assignment.buyer_user_id, assignment_id=assignment.id
            )

    # verifies that declining frees the listing and the queue place
    async def test_frees_the_listing_and_the_queue_place(self) -> None:
        assignment = _assignment()
        listing = SimpleNamespace(state=MarketListingState.assigned)
        entry = SimpleNamespace(left_at=None)
        service, _ = _make_service(assignment=assignment, listing=listing, queue_entry=entry)
        await service.decline_assignment(
            user_id=assignment.buyer_user_id, assignment_id=assignment.id
        )
        assert assignment.state == MarketAssignmentState.declined
        assert listing.state == MarketListingState.available
        assert entry.left_at is not None


class TestReads:
    # verifies that another user's assignment is never returned
    async def test_get_assignment_rejects_another_owner(self) -> None:
        service, _ = _make_service(assignment=_assignment())
        with pytest.raises(MarketError, match="Assignment not found"):
            await service.get_assignment(user_id=uuid.uuid4(), assignment_id=uuid.uuid4())

    # verifies that the owner gets their assignment back
    async def test_get_assignment_returns_it_to_its_owner(self) -> None:
        assignment = _assignment()
        service, _ = _make_service(assignment=assignment)
        result = await service.get_assignment(
            user_id=assignment.buyer_user_id, assignment_id=assignment.id
        )
        assert result is assignment

    # verifies that the recent list is read within a window
    async def test_lists_recent_assignments(self) -> None:
        service, repo = _make_service()
        assert await service.list_recent_assignments(user_id=uuid.uuid4()) == []
        repo.list_recent_assignments_for_user.assert_awaited_once()
