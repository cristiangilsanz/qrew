"""Organisations, venues, events and the tiers put on sale."""

from __future__ import annotations

from decimal import Decimal

from .models import Event, Organisation, TicketType, Venue

GENERAL = TicketType(
    key="general",
    name="General",
    capacity=200,
    reserved=12,
    price_cents=2500,
    position=1,
)
VIP = TicketType(
    key="vip", name="VIP", capacity=40, reserved=6, price_cents=7500, position=2
)
SOLD_OUT = TicketType(
    key="early",
    name="Early Bird",
    capacity=20,
    reserved=20,
    price_cents=1500,
    position=0,
)

ORGANISATIONS = (
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

VENUES = (
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

EVENTS = (
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
        ticket_types=(SOLD_OUT, GENERAL, VIP),
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
        ticket_types=(GENERAL, VIP),
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
        ticket_types=(GENERAL,),
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
        ticket_types=(GENERAL,),
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
        ticket_types=(GENERAL,),
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
        ticket_types=(GENERAL, VIP),
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
        ticket_types=(GENERAL,),
    ),
)
