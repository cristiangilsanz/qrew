import phonenumbers
import zxcvbn
from MailChecker import MailChecker  # type: ignore[import-untyped]
from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator

_PASSWORD_SECURITY_MIN_SCORE = 3


class RegisterRequest(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=255)

    email: EmailStr

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        """Reject emails from known disposable address providers."""
        if not MailChecker.is_valid(v):  # type: ignore[no-untyped-call]
            raise ValueError("Disposable email addresses are not allowed")
        return v.lower()

    phone_number: str = Field(..., min_length=7, max_length=20)

    @field_validator("phone_number")
    @classmethod
    def validate_phone_number(cls, v: str) -> str:
        """Reject phone numbers that are not valid for their region."""
        try:
            parsed = phonenumbers.parse(v, None)
        except phonenumbers.NumberParseException as exc:
            raise ValueError("Invalid phone number") from exc
        if not phonenumbers.is_valid_number(parsed):
            raise ValueError("Phone number is not valid for its region")
        return v

    password: str = Field(..., min_length=8)

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Reject weak passwords."""
        result = zxcvbn.zxcvbn(v)
        if result["score"] < _PASSWORD_SECURITY_MIN_SCORE:
            feedback = result["feedback"]["warning"] or "Password is too weak"
            raise ValueError(feedback)
        return v

    terms_accepted: bool

    @model_validator(mode="after")
    def validate_terms_accepted(self) -> "RegisterRequest":
        """Require that T&Cs have been accepted."""
        if not self.terms_accepted:
            raise ValueError("You must accept the terms and conditions to register")
        return self

    captcha_token: str = Field(..., min_length=1, max_length=2048)


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
    def validate_phone_number(cls, v: str) -> str:
        """Reject phone numbers that are not valid for their region."""
        try:
            parsed = phonenumbers.parse(v, None)
        except phonenumbers.NumberParseException as exc:
            raise ValueError("Invalid phone number") from exc
        if not phonenumbers.is_valid_number(parsed):
            raise ValueError("Phone number is not valid for its region")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1)


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"  # noqa: S105


class VerifyResponse(BaseModel):
    message: str
