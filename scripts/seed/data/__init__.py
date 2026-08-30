# aggregates the seed data modules into one dataset

from __future__ import annotations

from .catalog import EVENTS, ORGANISATIONS, VENUES
from .entry import SCANNERS, SCANS
from .identity import DEVICES, PEOPLE
from .models import CURRENCY, PASSWORD, Dataset
from .payments import PAYMENTS
from .sales import ASSIGNMENTS, LISTINGS, QUEUE, RESERVATIONS
from .ticketing import TICKETS

__all__ = ["CURRENCY", "PASSWORD", "SCANNERS", "Dataset", "build", "build_accounts"]


# assembles the full seeded dataset from every domain module
def build() -> Dataset:
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


# assembles a dataset holding only the accounts and their devices
def build_accounts() -> Dataset:
    return Dataset(
        people=PEOPLE,
        organisations=(),
        venues=(),
        events=(),
        reservations=(),
        tickets=(),
        listings=(),
        assignments=(),
        payments=(),
        queue=(),
        scans=(),
        devices=DEVICES,
    )
