from pydantic import BaseModel, EmailStr, Field, field_validator

from com.qode.qrew.v1.service.schemas._validators import (
    validate_non_disposable_email,
    validate_phone_number,
    validate_strong_password,
)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8)

    @field_validator("new_password")
    @classmethod
    def _v_new_password(cls, v: str) -> str:
        """Reject weak passwords."""
        return validate_strong_password(v)


class ChangePasswordResponse(BaseModel):
    message: str


class ChangeEmailRequest(BaseModel):
    new_email: EmailStr
    current_password: str = Field(..., min_length=1)

    @field_validator("new_email")
    @classmethod
    def _v_new_email(cls, v: str) -> str:
        """Reject disposable email addresses."""
        return validate_non_disposable_email(v)


class ConfirmEmailChangeRequest(BaseModel):
    token: str = Field(..., min_length=1, max_length=512)


class ChangeEmailResponse(BaseModel):
    message: str


class ChangePhoneRequest(BaseModel):
    new_phone_number: str = Field(..., min_length=7, max_length=20)
    current_password: str = Field(..., min_length=1)

    @field_validator("new_phone_number")
    @classmethod
    def _v_new_phone(cls, v: str) -> str:
        """Reject invalid phone numbers."""
        return validate_phone_number(v)


class ConfirmPhoneChangeRequest(BaseModel):
    new_phone_number: str = Field(..., min_length=7, max_length=20)
    otp: str = Field(..., min_length=6, max_length=6, pattern=r"^\d{6}$")


class ChangePhoneResponse(BaseModel):
    message: str


class AccountDeleteRequest(BaseModel):
    current_password: str = Field(..., min_length=1)


class AccountDeleteResponse(BaseModel):
    message: str


class RecoveryBeginResponse(BaseModel):
    message: str
    recovery_token: str | None = None
    passkey_options: str | None = None


class RecoveryCompleteResponse(BaseModel):
    message: str
