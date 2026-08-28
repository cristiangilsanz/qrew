# defines the data schemas for identity's domain events
from __future__ import annotations

import uuid

from pydantic import BaseModel

from contracts.messaging.envelope import EventEnvelope


class UserRegisteredData(BaseModel):
    user_id: uuid.UUID
    registered_at: str
    phone_e164: str | None = None


class UserVerifiedData(BaseModel):
    user_id: uuid.UUID


class DeviceBoundData(BaseModel):
    device_id: uuid.UUID
    user_id: uuid.UUID
    platform: str


class DeviceRevokedData(BaseModel):
    device_id: uuid.UUID
    user_id: uuid.UUID
    reason: str


class SessionEvictedData(BaseModel):
    session_id: uuid.UUID
    user_id: uuid.UUID
    reason: str


class PasskeyReassertedData(BaseModel):
    user_id: uuid.UUID
    device_id: uuid.UUID


# parses an envelope into a user registered payload
def user_registered(envelope: EventEnvelope) -> UserRegisteredData:
    return UserRegisteredData(**envelope.data)


# parses an envelope into a device revoked payload
def device_revoked(envelope: EventEnvelope) -> DeviceRevokedData:
    return DeviceRevokedData(**envelope.data)
