"""The catalogue of fixtures, declared once and consumed by every writer.

Names follow a deliberate pattern, Admin, Manager, Member and User A to C for people,
Org A and Org B for organisations, Venue A to C for venues and Event A to G for events,
so that a scenario can be described in a sentence: "User A holds an issued ticket for
Event C at Venue C". Everything that carries a time is expressed against the moment the
seeder runs.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal

from .clock import Timeline
from .ids import ident

PASSWORD = "Password1!"  # noqa: S105  fixture credential, never a real secret
CURRENCY = "EUR"


@dataclass(frozen=True)
class Person:
    key: str
    name: str
    email: str
    phone: str
    kyc: str = "approved"
    admin: bool = False
    national_id: str | None = None
    verified: bool = True

    @property
    def id(self) -> uuid.UUID:
        return ident("user", self.key)


@dataclass(frozen=True)
class Organisation:
    key: str
    slug: str
    name: str
    description: str
    members: tuple[tuple[str, str], ...]

    @property
    def id(self) -> uuid.UUID:
        return ident("organisation", self.key)


@dataclass(frozen=True)
class Venue:
    key: str
    name: str
    address: str
    city: str
    country: str
    latitude: Decimal
    longitude: Decimal
    radius_m: int
    timezone: str

    @property
    def id(self) -> uuid.UUID:
        return ident("venue", self.key)


@dataclass(frozen=True)
class TicketType:
    key: str
    name: str
    capacity: int
    reserved: int
    price_cents: int
    position: int

    def id(self, event_key: str) -> uuid.UUID:
        return ident("ticket-type", event_key, self.key)


@dataclass(frozen=True)
class Event:
    key: str
    name: str
    description: str
    status: str
    organisation: str
    venue: str
    starts_in_hours: float
    duration_hours: float
    sale_opens_in_hours: float
    sale_closes_in_hours: float
    ticket_types: tuple[TicketType, ...]
    queue_required: bool = False
    queue_rate: int = 60
    max_per_user: int = 4

    @property
    def id(self) -> uuid.UUID:
        return ident("event", self.key)

    def starts_at(self, when: Timeline) -> datetime:
        return when.hours(self.starts_in_hours)

    def ends_at(self, when: Timeline) -> datetime:
        return when.hours(self.starts_in_hours + self.duration_hours)

    def sale_starts_at(self, when: Timeline) -> datetime:
        return when.hours(self.sale_opens_in_hours)

    def sale_ends_at(self, when: Timeline) -> datetime:
        return when.hours(self.sale_closes_in_hours)


@dataclass(frozen=True)
class Reservation:
    key: str
    user: str
    event: str
    ticket_type: str
    quantity: int
    status: str
    created_hours_ago: float
    expires_in_minutes: float
    holders: tuple[tuple[str, str], ...] = ()
    requires_review: bool = False
    risk_score: int = 0

    @property
    def id(self) -> uuid.UUID:
        return ident("reservation", self.key)


@dataclass(frozen=True)
class Ticket:
    key: str
    reservation: str | None
    user: str
    event: str
    ticket_type: str
    state: str
    issued_hours_ago: float
    holder_name: str
    holder_dni: str
    bound_device: str | None = None
    expired_hours_ago: float | None = None

    @property
    def id(self) -> uuid.UUID:
        return ident("ticket", self.key)


@dataclass(frozen=True)
class Listing:
    key: str
    ticket: str
    event: str
    ticket_type: str
    seller: str
    price_cents: int
    state: str
    listed_hours_ago: float
    expires_in_hours: float
    completed: bool = False
    cancelled: bool = False

    @property
    def id(self) -> uuid.UUID:
        return ident("listing", self.key)


@dataclass(frozen=True)
class Assignment:
    key: str
    listing: str
    event: str
    buyer: str
    state: str
    assigned_minutes_ago: float
    expires_in_minutes: float
    holder_name: str
    holder_dni: str
    paid: bool = False

    @property
    def id(self) -> uuid.UUID:
        return ident("assignment", self.key)


@dataclass(frozen=True)
class Payment:
    key: str
    user: str
    reservation: str | None
    assignment: str | None
    amount_cents: int
    status: str
    created_hours_ago: float

    @property
    def id(self) -> uuid.UUID:
        return ident("payment", self.key)


@dataclass(frozen=True)
class Scan:
    key: str
    ticket: str
    event: str
    scanner: str
    allowed: bool
    reason: str | None
    minutes_ago: float

    @property
    def id(self) -> uuid.UUID:
        return ident("scan", self.key)


@dataclass(frozen=True)
class Dataset:
    people: tuple[Person, ...]
    organisations: tuple[Organisation, ...]
    venues: tuple[Venue, ...]
    events: tuple[Event, ...]
    reservations: tuple[Reservation, ...]
    tickets: tuple[Ticket, ...]
    listings: tuple[Listing, ...]
    assignments: tuple[Assignment, ...]
    payments: tuple[Payment, ...]
    queue: tuple[tuple[str, str, int], ...]
    scans: tuple[Scan, ...]
    devices: tuple[tuple[str, str], ...] = field(default=())

    def person(self, key: str) -> Person:
        return next(p for p in self.people if p.key == key)

    def event(self, key: str) -> Event:
        return next(e for e in self.events if e.key == key)

    def venue(self, key: str) -> Venue:
        return next(v for v in self.venues if v.key == key)

    def ticket(self, key: str) -> Ticket:
        return next(t for t in self.tickets if t.key == key)

    def listing(self, key: str) -> Listing:
        return next(x for x in self.listings if x.key == key)

    def ticket_type(self, event_key: str, type_key: str) -> TicketType:
        return next(t for t in self.event(event_key).ticket_types if t.key == type_key)


_GENERAL = TicketType(
    key="general",
    name="General",
    capacity=200,
    reserved=12,
    price_cents=2500,
    position=1,
)
_VIP = TicketType(
    key="vip", name="VIP", capacity=40, reserved=6, price_cents=7500, position=2
)
_SOLD_OUT = TicketType(
    key="early",
    name="Early Bird",
    capacity=20,
    reserved=20,
    price_cents=1500,
    position=0,
)


def build() -> Dataset:
    """Returns the fixture catalogue.

    Admin is the account to test with. It owns an organisation, holds tickets in every
    state, sells and buys on the market and has a payment of each outcome, so almost any
    screen can be reached without switching accounts. The rest exist to exercise what
    needs a second party: Manager runs a separate organisation, Member works the gate,
    User A trades with Admin, User B waits in the queue and User C is a fresh account.
    """
    people = (
        Person(
            key="admin",
            name="Admin",
            email="admin@qrew.test",
            phone="+34600000001",
            admin=True,
            national_id="00000001A",
        ),
        Person(
            key="manager",
            name="Manager",
            email="manager@qrew.test",
            phone="+34600000002",
            national_id="00000002B",
        ),
        Person(
            key="member",
            name="Member",
            email="member@qrew.test",
            phone="+34600000003",
            national_id="00000003C",
        ),
        Person(
            key="user-a",
            name="User A",
            email="user-a@qrew.test",
            phone="+34600000004",
            national_id="00000004D",
        ),
        Person(
            key="user-b",
            name="User B",
            email="user-b@qrew.test",
            phone="+34600000005",
            national_id="00000005E",
        ),
        Person(
            key="user-c",
            name="User C",
            email="user-c@qrew.test",
            phone="+34600000006",
            kyc="not_submitted",
            national_id=None,
            verified=False,
        ),
    )

    organisations = (
        Organisation(
            key="org-a",
            slug="org-a",
            name="Org A",
            description="Admin owns it and runs every event used for testing.",
            members=(("admin", "owner"), ("manager", "manager"), ("member", "member")),
        ),
        Organisation(
            key="org-b",
            slug="org-b",
            name="Org B",
            description="Belongs to Manager alone, to check the boundary between them.",
            members=(("manager", "owner"),),
        ),
    )

    venues = (
        Venue(
            key="venue-a",
            name="Venue A",
            address="Calle A 1",
            city="Madrid",
            country="ES",
            latitude=Decimal("40.416775"),
            longitude=Decimal("-3.703790"),
            radius_m=200,
            timezone="Europe/Madrid",
        ),
        Venue(
            key="venue-b",
            name="Venue B",
            address="Carrer B 2",
            city="Barcelona",
            country="ES",
            latitude=Decimal("41.385064"),
            longitude=Decimal("2.173404"),
            radius_m=350,
            timezone="Europe/Madrid",
        ),
        Venue(
            key="venue-c",
            name="Venue C",
            address="Carrer C 3",
            city="Valencia",
            country="ES",
            latitude=Decimal("39.469907"),
            longitude=Decimal("-0.376288"),
            radius_m=120,
            timezone="Europe/Madrid",
        ),
    )

    events = (
        Event(
            key="event-a",
            name="Event A",
            description="Published and on sale right now.",
            status="published",
            organisation="org-a",
            venue="venue-a",
            starts_in_hours=24 * 14,
            duration_hours=3,
            sale_opens_in_hours=-24 * 7,
            sale_closes_in_hours=24 * 13,
            ticket_types=(_SOLD_OUT, _GENERAL, _VIP),
        ),
        Event(
            key="event-b",
            name="Event B",
            description="Published, with the sale still to open.",
            status="published",
            organisation="org-a",
            venue="venue-b",
            starts_in_hours=24 * 30,
            duration_hours=4,
            sale_opens_in_hours=48,
            sale_closes_in_hours=24 * 29,
            ticket_types=(_GENERAL, _VIP),
        ),
        Event(
            key="event-c",
            name="Event C",
            description="Running now, for validation at the gate.",
            status="ongoing",
            organisation="org-a",
            venue="venue-c",
            starts_in_hours=-1,
            duration_hours=5,
            sale_opens_in_hours=-24 * 20,
            sale_closes_in_hours=-2,
            ticket_types=(_GENERAL,),
        ),
        Event(
            key="event-d",
            name="Event D",
            description="Draft, visible only to its organisation.",
            status="draft",
            organisation="org-a",
            venue="venue-a",
            starts_in_hours=24 * 60,
            duration_hours=2,
            sale_opens_in_hours=24 * 30,
            sale_closes_in_hours=24 * 59,
            ticket_types=(_GENERAL,),
        ),
        Event(
            key="event-e",
            name="Event E",
            description="Cancelled after being published.",
            status="cancelled",
            organisation="org-a",
            venue="venue-b",
            starts_in_hours=24 * 21,
            duration_hours=3,
            sale_opens_in_hours=-24 * 3,
            sale_closes_in_hours=24 * 20,
            ticket_types=(_GENERAL,),
        ),
        Event(
            key="event-f",
            name="Event F",
            description="High demand, admission queue required.",
            status="published",
            organisation="org-a",
            venue="venue-a",
            starts_in_hours=24 * 45,
            duration_hours=3,
            sale_opens_in_hours=0.25,
            sale_closes_in_hours=24 * 44,
            ticket_types=(_GENERAL, _VIP),
            queue_required=True,
            queue_rate=30,
            max_per_user=2,
        ),
        Event(
            key="event-g",
            name="Event G",
            description="Finished yesterday, kept for history.",
            status="ongoing",
            organisation="org-b",
            venue="venue-c",
            starts_in_hours=-30,
            duration_hours=4,
            sale_opens_in_hours=-24 * 40,
            sale_closes_in_hours=-31,
            ticket_types=(_GENERAL,),
        ),
    )

    reservations = (
        Reservation(
            key="paid-admin",
            user="admin",
            event="event-a",
            ticket_type="general",
            quantity=2,
            status="paid",
            created_hours_ago=48,
            expires_in_minutes=-2865,
            holders=(("Admin", "00000001A"), ("Guest One", "00000010K")),
        ),
        Reservation(
            key="pending-admin",
            user="admin",
            event="event-a",
            ticket_type="vip",
            quantity=1,
            status="reserved",
            created_hours_ago=0.1,
            expires_in_minutes=9,
            holders=(("Admin", "00000001A"),),
        ),
        Reservation(
            key="expired-admin",
            user="admin",
            event="event-a",
            ticket_type="general",
            quantity=1,
            status="expired",
            created_hours_ago=6,
            expires_in_minutes=-330,
        ),
        Reservation(
            key="cancelled-admin",
            user="admin",
            event="event-b",
            ticket_type="general",
            quantity=1,
            status="cancelled",
            created_hours_ago=12,
            expires_in_minutes=-705,
        ),
        Reservation(
            key="review-admin",
            user="admin",
            event="event-a",
            ticket_type="vip",
            quantity=2,
            status="reserved",
            created_hours_ago=0.2,
            expires_in_minutes=7,
            holders=(("Admin", "00000001A"), ("Guest Two", "00000011L")),
            requires_review=True,
            risk_score=72,
        ),
        Reservation(
            key="gate-admin",
            user="admin",
            event="event-c",
            ticket_type="general",
            quantity=2,
            status="paid",
            created_hours_ago=72,
            expires_in_minutes=-4305,
            holders=(("Admin", "00000001A"), ("Guest Two", "00000011L")),
        ),
        Reservation(
            key="vip-admin",
            user="admin",
            event="event-a",
            ticket_type="vip",
            quantity=1,
            status="paid",
            created_hours_ago=21,
            expires_in_minutes=-1245,
            holders=(("Admin", "00000001A"),),
        ),
        Reservation(
            key="cancelled-event-admin",
            user="admin",
            event="event-e",
            ticket_type="general",
            quantity=1,
            status="paid",
            created_hours_ago=31,
            expires_in_minutes=-1845,
            holders=(("Admin", "00000001A"),),
        ),
        Reservation(
            key="vip-user-a",
            user="user-a",
            event="event-a",
            ticket_type="vip",
            quantity=1,
            status="paid",
            created_hours_ago=29,
            expires_in_minutes=-1725,
            holders=(("User A", "00000004D"),),
        ),
        Reservation(
            key="past-admin",
            user="admin",
            event="event-g",
            ticket_type="general",
            quantity=2,
            status="paid",
            created_hours_ago=24 * 5,
            expires_in_minutes=-7185,
        ),
        Reservation(
            key="paid-user-a",
            user="user-a",
            event="event-a",
            ticket_type="general",
            quantity=1,
            status="paid",
            created_hours_ago=30,
            expires_in_minutes=-1785,
            holders=(("User A", "00000004D"),),
        ),
    )

    tickets = (
        Ticket(
            key="issued-admin",
            reservation="paid-admin",
            user="admin",
            event="event-a",
            ticket_type="general",
            state="issued",
            issued_hours_ago=47,
            holder_name="Admin",
            holder_dni="00000001A",
            bound_device="admin",
        ),
        Ticket(
            key="on-sale-admin",
            reservation="paid-admin",
            user="admin",
            event="event-a",
            ticket_type="general",
            state="on_sale",
            issued_hours_ago=47,
            holder_name="Guest One",
            holder_dni="00000010K",
        ),
        Ticket(
            key="gate-admin",
            reservation="gate-admin",
            user="admin",
            event="event-c",
            ticket_type="general",
            state="issued",
            issued_hours_ago=71,
            holder_name="Admin",
            holder_dni="00000001A",
            bound_device="admin",
        ),
        Ticket(
            key="scanning-admin",
            reservation="gate-admin",
            user="admin",
            event="event-c",
            ticket_type="general",
            state="scanning",
            issued_hours_ago=70,
            holder_name="Guest Two",
            holder_dni="00000011L",
            bound_device="admin",
        ),
        Ticket(
            key="redeemed-admin",
            reservation="past-admin",
            user="admin",
            event="event-g",
            ticket_type="general",
            state="redeemed",
            issued_hours_ago=24 * 4,
            holder_name="Admin",
            holder_dni="00000001A",
            bound_device="admin",
        ),
        Ticket(
            key="expired-admin",
            reservation="past-admin",
            user="admin",
            event="event-g",
            ticket_type="general",
            state="expired",
            issued_hours_ago=24 * 4,
            holder_name="Guest Two",
            holder_dni="00000011L",
            expired_hours_ago=25,
        ),
        Ticket(
            key="flagged-admin",
            reservation="vip-admin",
            user="admin",
            event="event-a",
            ticket_type="vip",
            state="flagged",
            issued_hours_ago=20,
            holder_name="Admin",
            holder_dni="00000001A",
        ),
        Ticket(
            key="cancelled-admin",
            reservation="cancelled-event-admin",
            user="admin",
            event="event-e",
            ticket_type="general",
            state="cancelled",
            issued_hours_ago=30,
            holder_name="Admin",
            holder_dni="00000001A",
        ),
        Ticket(
            key="issued-user-a",
            reservation="paid-user-a",
            user="user-a",
            event="event-a",
            ticket_type="general",
            state="issued",
            issued_hours_ago=29,
            holder_name="User A",
            holder_dni="00000004D",
            bound_device="user-a",
        ),
        Ticket(
            key="on-sale-user-a",
            reservation="vip-user-a",
            user="user-a",
            event="event-a",
            ticket_type="vip",
            state="on_sale",
            issued_hours_ago=28,
            holder_name="User A",
            holder_dni="00000004D",
        ),
    )

    listings = (
        Listing(
            key="available-admin",
            ticket="on-sale-admin",
            event="event-a",
            ticket_type="general",
            seller="admin",
            price_cents=_GENERAL.price_cents,
            state="available",
            listed_hours_ago=3,
            expires_in_hours=24 * 4,
        ),
        Listing(
            key="assigned-admin",
            ticket="issued-admin",
            event="event-a",
            ticket_type="general",
            seller="admin",
            price_cents=_GENERAL.price_cents,
            state="assigned",
            listed_hours_ago=2,
            expires_in_hours=24 * 3,
        ),
        Listing(
            key="completed-admin",
            ticket="redeemed-admin",
            event="event-g",
            ticket_type="general",
            seller="admin",
            price_cents=_GENERAL.price_cents,
            state="completed",
            listed_hours_ago=24 * 6,
            expires_in_hours=-24 * 2,
            completed=True,
        ),
        Listing(
            key="cancelled-admin",
            ticket="flagged-admin",
            event="event-a",
            ticket_type="vip",
            seller="admin",
            price_cents=_VIP.price_cents,
            state="cancelled",
            listed_hours_ago=24,
            expires_in_hours=-1,
            cancelled=True,
        ),
        Listing(
            key="offer-user-a",
            ticket="on-sale-user-a",
            event="event-a",
            ticket_type="vip",
            seller="user-a",
            price_cents=_VIP.price_cents,
            state="available",
            listed_hours_ago=5,
            expires_in_hours=24 * 2,
        ),
    )

    assignments = (
        Assignment(
            key="claim-admin",
            listing="offer-user-a",
            event="event-a",
            buyer="admin",
            state="pending",
            assigned_minutes_ago=3,
            expires_in_minutes=12,
            holder_name="Admin",
            holder_dni="00000001A",
        ),
        Assignment(
            key="pending-user-b",
            listing="assigned-admin",
            event="event-a",
            buyer="user-b",
            state="pending",
            assigned_minutes_ago=4,
            expires_in_minutes=11,
            holder_name="User B",
            holder_dni="00000005E",
        ),
        Assignment(
            key="paid-user-b",
            listing="completed-admin",
            event="event-g",
            buyer="user-b",
            state="paid",
            assigned_minutes_ago=24 * 60 * 5,
            expires_in_minutes=-7185,
            holder_name="User B",
            holder_dni="00000005E",
            paid=True,
        ),
        Assignment(
            key="expired-user-c",
            listing="cancelled-admin",
            event="event-a",
            buyer="user-c",
            state="expired",
            assigned_minutes_ago=120,
            expires_in_minutes=-105,
            holder_name="User C",
            holder_dni="00000006F",
        ),
    )

    payments = (
        Payment(
            key="succeeded-admin",
            user="admin",
            reservation="paid-admin",
            assignment=None,
            amount_cents=_GENERAL.price_cents * 2,
            status="succeeded",
            created_hours_ago=47.9,
        ),
        Payment(
            key="processing-admin",
            user="admin",
            reservation="pending-admin",
            assignment=None,
            amount_cents=_VIP.price_cents,
            status="processing",
            created_hours_ago=0.05,
        ),
        Payment(
            key="failed-admin",
            user="admin",
            reservation="cancelled-admin",
            assignment=None,
            amount_cents=_GENERAL.price_cents,
            status="failed",
            created_hours_ago=11.9,
        ),
        Payment(
            key="refunded-admin",
            user="admin",
            reservation="past-admin",
            assignment=None,
            amount_cents=_GENERAL.price_cents * 2,
            status="refunded",
            created_hours_ago=24 * 4,
        ),
        Payment(
            key="action-admin",
            user="admin",
            reservation=None,
            assignment="claim-admin",
            amount_cents=_VIP.price_cents,
            status="requires_action",
            created_hours_ago=0.04,
        ),
        Payment(
            key="succeeded-user-a",
            user="user-a",
            reservation="paid-user-a",
            assignment=None,
            amount_cents=_GENERAL.price_cents,
            status="succeeded",
            created_hours_ago=29.9,
        ),
    )

    queue = (
        ("event-f", "admin", 1),
        ("event-f", "user-a", 2),
        ("event-f", "user-b", 3),
    )

    scans = (
        Scan(
            key="allowed-admin",
            ticket="redeemed-admin",
            event="event-g",
            scanner="gate-c",
            allowed=True,
            reason=None,
            minutes_ago=24 * 60 + 30,
        ),
        Scan(
            key="denied-admin",
            ticket="scanning-admin",
            event="event-c",
            scanner="gate-c",
            allowed=False,
            reason="geofence",
            minutes_ago=12,
        ),
    )

    devices = (
        ("admin", "Device Admin"),
        ("user-a", "Device A"),
        ("user-b", "Device B"),
    )

    return Dataset(
        people=people,
        organisations=organisations,
        venues=venues,
        events=events,
        reservations=reservations,
        tickets=tickets,
        listings=listings,
        assignments=assignments,
        payments=payments,
        queue=queue,
        scans=scans,
        devices=devices,
    )
