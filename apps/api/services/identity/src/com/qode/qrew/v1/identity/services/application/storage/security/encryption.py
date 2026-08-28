# decides which storage kinds are encrypted at rest
from com.qode.qrew.v1.identity.core.utils import pii as pii_crypto

ENCRYPTED_KINDS = frozenset({"kyc"})


# checks whether a storage kind must be encrypted
def should_encrypt(kind: str) -> bool:
    return kind in ENCRYPTED_KINDS


# encrypts content for storage
def encrypt(content: bytes) -> bytes:
    return pii_crypto.encrypt_bytes(content)


# decrypts stored content back to plaintext
def decrypt(content: bytes) -> bytes:
    return pii_crypto.decrypt_bytes(content)
