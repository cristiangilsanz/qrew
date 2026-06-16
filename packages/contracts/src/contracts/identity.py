from __future__ import annotations

import uuid

from pydantic import BaseModel

from contracts.envelope import EventEnvelope


class UserRegisteredData(BaseModel):
    email: str
    display_name: str


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


def user_registered(envelope: EventEnvelope) -> UserRegisteredData:
    return UserRegisteredData(**envelope.data)


def device_revoked(envelope: EventEnvelope) -> DeviceRevokedData:
    return DeviceRevokedData(**envelope.data)
