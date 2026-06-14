from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator

from com.qode.qrew.v1.identity.schemas._validators import (
    validate_non_disposable_email,
    validate_phone_number,
    validate_strong_password,
)


class RegisterRequest(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=255)
    email: EmailStr
    phone_number: str = Field(..., min_length=7, max_length=20)
    password: str = Field(..., min_length=8)
    terms_accepted: bool
    captcha_token: str = Field(..., min_length=1, max_length=2048)

    @field_validator("email")
    @classmethod
    def _v_email(cls, v: str) -> str:
        """Reject disposable email addresses."""
        return validate_non_disposable_email(v)

    @field_validator("phone_number")
    @classmethod
    def _v_phone(cls, v: str) -> str:
        """Reject invalid phone numbers."""
        return validate_phone_number(v)

    @field_validator("password")
    @classmethod
    def _v_password(cls, v: str) -> str:
        """Reject weak passwords."""
        return validate_strong_password(v)

    @model_validator(mode="after")
    def _v_terms(self) -> "RegisterRequest":
        """Require that the terms and conditions are accepted."""
        if not self.terms_accepted:
            raise ValueError("You must accept the terms and conditions to register")
        return self


class RegisterResponse(BaseModel):
    id: str
    message: str


class VerifyEmailRequest(BaseModel):
    token: str = Field(..., min_length=1, max_length=512)


class VerifyPhoneRequest(BaseModel):
    phone_number: str = Field(..., min_length=7, max_length=20)
    otp: str = Field(..., min_length=6, max_length=6, pattern=r"^\d{6}$")

    @field_validator("phone_number")
    @classmethod
    def _v_phone(cls, v: str) -> str:
        """Reject invalid phone numbers."""
        return validate_phone_number(v)


class VerifyResponse(BaseModel):
    message: str


class ResendEmailVerificationRequest(BaseModel):
    email: EmailStr


class ResendPhoneOtpRequest(BaseModel):
    phone_number: str = Field(..., min_length=7, max_length=20)

    @field_validator("phone_number")
    @classmethod
    def _v_phone(cls, v: str) -> str:
        """Reject invalid phone numbers."""
        return validate_phone_number(v)


class ResendResponse(BaseModel):
    message: str
