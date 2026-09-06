# defines the data schemas for identity's domain events
from __future__ import annotations

import uuid
from datetime import datetime
from typing import ClassVar

from pydantic import BaseModel

from contracts.messaging.envelope import EventEnvelope


class UserRegisteredData(BaseModel):
    SUBJECT: ClassVar[str] = "identity.user.registered.v1"

    user_id: uuid.UUID
    registered_at: datetime
    phone_e164: str | None = None


class FingerprintSeenData(BaseModel):
    SUBJECT: ClassVar[str] = "identity.fingerprint.seen.v1"

    fingerprint_hash: str


class DeviceAttestedData(BaseModel):
    SUBJECT: ClassVar[str] = "identity.device.attested.v1"

    device_id: uuid.UUID
    user_id: uuid.UUID
    attested_at: datetime
    platform: str | None = None


class DeviceRevokedData(BaseModel):
    SUBJECT: ClassVar[str] = "identity.device.revoked.v1"

    device_id: uuid.UUID
    user_id: uuid.UUID
    revoked_at: datetime


# parses an envelope into a user registered payload
def user_registered(envelope: EventEnvelope) -> UserRegisteredData:
    return UserRegisteredData(**envelope.data)


# parses an envelope into a device revoked payload
def device_revoked(envelope: EventEnvelope) -> DeviceRevokedData:
    return DeviceRevokedData(**envelope.data)
