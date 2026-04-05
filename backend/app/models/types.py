"""Custom SQLAlchemy column types for NEX Payroll.

EncryptedString — Fernet (AES-256) encryption for PII fields.
Encrypts on write, decrypts on read. Stored as base64-encoded ciphertext.
"""

import os

from cryptography.fernet import Fernet
from sqlalchemy import Text
from sqlalchemy.types import TypeDecorator

# Fernet key from environment — MUST be set in production.
# Generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
_FERNET_KEY = os.environ.get("FERNET_KEY", "")


def _get_fernet() -> Fernet:
    """Return a Fernet instance, raising if key is not configured."""
    if not _FERNET_KEY:
        raise RuntimeError(
            "FERNET_KEY environment variable is not set. "
            "Generate one with: python -c "
            '"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"'
        )
    return Fernet(_FERNET_KEY.encode())


class EncryptedString(TypeDecorator):
    """Encrypts/decrypts string values transparently using Fernet (AES-256).

    Stored in the database as Text (base64-encoded ciphertext).
    Application sees plaintext strings.

    Usage:
        birth_number: Mapped[str] = mapped_column(EncryptedString(), nullable=False)
    """

    impl = Text
    cache_ok = True

    def process_bind_param(self, value: str | None, dialect: object) -> str | None:
        """Encrypt plaintext → ciphertext before INSERT/UPDATE."""
        if value is None:
            return None
        fernet = _get_fernet()
        return fernet.encrypt(value.encode("utf-8")).decode("utf-8")

    def process_result_value(self, value: str | None, dialect: object) -> str | None:
        """Decrypt ciphertext → plaintext after SELECT."""
        if value is None:
            return None
        fernet = _get_fernet()
        return fernet.decrypt(value.encode("utf-8")).decode("utf-8")
