"""The shape of every fixture: what a person, an event or a ticket carries."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal

from ..core import Timeline, ident

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
