"""The fixture catalogue, one module per service.

Admin is the account to test with. It owns an organisation, holds tickets in every
state, sells and buys on the market and has a payment of each outcome, so almost any
screen can be reached without switching accounts. The rest exist to exercise what needs
a second party: Manager runs a separate organisation, Member works the gate, User A
trades with Admin, User B waits in the queue and User C is a fresh account.
"""

from __future__ import annotations

from .catalog import EVENTS, ORGANISATIONS, VENUES
from .entry import SCANNERS, SCANS
from .identity import DEVICES, PEOPLE
from .models import CURRENCY, PASSWORD, Dataset
from .payments import PAYMENTS
from .sales import ASSIGNMENTS, LISTINGS, QUEUE, RESERVATIONS
from .ticketing import TICKETS

__all__ = ["CURRENCY", "PASSWORD", "SCANNERS", "Dataset", "build"]


def build() -> Dataset:
    """Assembles the catalogue every writer consumes."""
    return Dataset(
        people=PEOPLE,
        organisations=ORGANISATIONS,
        venues=VENUES,
        events=EVENTS,
        reservations=RESERVATIONS,
        tickets=TICKETS,
        listings=LISTINGS,
        assignments=ASSIGNMENTS,
        payments=PAYMENTS,
        queue=QUEUE,
        scans=SCANS,
        devices=DEVICES,
    )
