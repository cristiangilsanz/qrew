# declares the fixture people and their devices

from __future__ import annotations

from .models import Person

PEOPLE = (
    Person(
        key="admin",
        name="Admin",
        email="admin@qrew.dev",
        phone="+34600000001",
        admin=True,
        national_id="00000001R",
    ),
    Person(
        key="manager",
        name="Manager",
        email="manager@qrew.dev",
        phone="+34600000002",
        national_id="00000002W",
    ),
    Person(
        key="member",
        name="Member",
        email="member@qrew.dev",
        phone="+34600000003",
        national_id="00000003A",
    ),
    Person(
        key="user-a",
        name="User A",
        email="user-a@qrew.dev",
        phone="+34600000004",
        national_id="00000004G",
    ),
    Person(
        key="user-b",
        name="User B",
        email="user-b@qrew.dev",
        phone="+34600000005",
        national_id="00000005M",
    ),
    Person(
        key="user-c",
        name="User C",
        email="user-c@qrew.dev",
        phone="+34600000006",
        kyc="not_submitted",
        national_id=None,
        verified=False,
    ),
)

DEVICES = (
    ("admin", "Device Admin"),
    ("user-a", "Device A"),
    ("user-b", "Device B"),
)
