# declares the fixture people and their devices

from __future__ import annotations

from .models import Person

PEOPLE = (
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

DEVICES = (
    ("admin", "Device Admin"),
    ("user-a", "Device A"),
    ("user-b", "Device B"),
)
