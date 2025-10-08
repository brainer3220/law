"""Token utilities for share links and embeds."""

from __future__ import annotations

import secrets
import string
from dataclasses import dataclass
from hashlib import sha256

_BASE62_ALPHABET = string.digits + string.ascii_letters


def base62_encode(value: int) -> str:
    """Encode *value* as a base62 string."""

    if value < 0:
        raise ValueError("value must be non-negative")
    if value == 0:
        return _BASE62_ALPHABET[0]
    base = len(_BASE62_ALPHABET)
    digits: list[str] = []
    while value:
        value, remainder = divmod(value, base)
        digits.append(_BASE62_ALPHABET[remainder])
    return "".join(reversed(digits))


@dataclass(slots=True)
class GeneratedToken:
    """Container for plaintext token and hashed representation."""

    token: str
    token_hash: str


def generate_token(num_bytes: int = 16) -> GeneratedToken:
    """Generate a cryptographically secure base62 token."""

    raw = secrets.token_bytes(num_bytes)
    token = base62_encode(int.from_bytes(raw, "big"))
    return GeneratedToken(
        token=token, token_hash=sha256(token.encode("utf-8")).hexdigest()
    )
