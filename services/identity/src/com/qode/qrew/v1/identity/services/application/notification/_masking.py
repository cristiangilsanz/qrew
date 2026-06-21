import re


def mask_email(email: str) -> str:
    """Partially obscures an email address for display in notifications."""
    try:
        local, domain = email.split("@", 1)
        if len(local) <= 2:
            masked_local = local[0] + "*"
        else:
            masked_local = local[0] + "*" * (len(local) - 2) + local[-1]
        return f"{masked_local}@{domain}"
    except ValueError:
        return "***@***"


def mask_phone_number(phone: str) -> str:
    """Partially obscures a phone number for display in notifications."""
    digits = re.sub(r"\D", "", phone)
    if len(digits) < 4:
        return "****"
    return "*" * (len(digits) - 4) + digits[-4:]
