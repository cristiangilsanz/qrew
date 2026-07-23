import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1)


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str | None = None
    token_type: str = "bearer"  # noqa: S105
    setup_required: bool = False
    password_compromised: bool = False


class RefreshRequest(BaseModel):
    refresh_token: str = Field(..., min_length=1)


class RefreshResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"  # noqa: S105


class LogoutRequest(BaseModel):
    refresh_token: str = Field(..., min_length=1)


class LogoutResponse(BaseModel):
    message: str


class UserProfileResponse(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str
    phone_number: str
    kyc_status: str
    email_verified: bool
    phone_verified: bool
    is_admin: bool
    created_at: datetime


class UserPublicProfile(BaseModel):
    id: uuid.UUID
    full_name: str
    email: str


class UserPublicProfilesRequest(BaseModel):
    user_ids: list[uuid.UUID]


class OnboardingStatusResponse(BaseModel):
    email_verified: bool
    phone_verified: bool
    kyc_submitted: bool
    passkey_registered: bool
    is_complete: bool
    current_step: Literal["email", "phone", "kyc", "passkey", "pending"]
