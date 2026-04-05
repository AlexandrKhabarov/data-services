import base64
import hashlib

from cryptography.fernet import Fernet


def _derive_fernet(raw_key: str) -> Fernet:
    """Derive a valid 32-byte Fernet key from an arbitrary string."""
    key_bytes = hashlib.sha256(raw_key.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(key_bytes))


def encrypt_session(session_string: str, raw_key: str) -> str:
    """Encrypt a Telethon StringSession for storage in the database."""
    return _derive_fernet(raw_key).encrypt(session_string.encode()).decode()


def decrypt_session(encrypted: str, raw_key: str) -> str:
    """Decrypt a stored Telethon StringSession."""
    return _derive_fernet(raw_key).decrypt(encrypted.encode()).decode()
