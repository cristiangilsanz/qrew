# validates phone numbers passwords and email addresses shared across schemas
import phonenumbers
import zxcvbn
from MailChecker import MailChecker  # type: ignore[import-untyped]

PASSWORD_SECURITY_MIN_SCORE = 3


# rejects a phone number that is not valid for its region
def validate_phone_number(v: str) -> str:
    try:
        parsed = phonenumbers.parse(v, None)
    except phonenumbers.NumberParseException as exc:
        raise ValueError("Phone number rejected.") from exc
    if not phonenumbers.is_valid_number(parsed):
        raise ValueError("Phone number rejected.")
    return v


# rejects a password below the minimum strength score
def validate_strong_password(v: str) -> str:
    result = zxcvbn.zxcvbn(v)
    if result["score"] < PASSWORD_SECURITY_MIN_SCORE:
        feedback = result["feedback"]["warning"] or "Password is too weak"
        raise ValueError(feedback)
    return v


# rejects an email address from a disposable domain
def validate_non_disposable_email(v: str) -> str:
    if not MailChecker.is_valid(v):  # type: ignore[no-untyped-call]
        raise ValueError("Disposable email rejected.")
    return v.lower()
