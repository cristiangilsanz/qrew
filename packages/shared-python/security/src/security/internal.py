# compares internal service keys in constant time
import hmac


# checks a provided internal key against the expected one
def matches_internal_key(provided: str, expected: str) -> bool:
    if not expected or not provided:
        return False
    return hmac.compare_digest(provided, expected)
