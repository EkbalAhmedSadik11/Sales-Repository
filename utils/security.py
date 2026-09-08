"""PIN hashing helpers for the Admin section.

Uses PBKDF2-HMAC-SHA256 from the stdlib hashlib module (no bcrypt/passlib
dependency, which keeps buildozer's compiled-dependency surface small).
The PIN is never stored or logged in plain text.
"""

import hashlib
import os
import hmac

_ITERATIONS = 200_000


def hash_pin(pin: str, salt: bytes = None) -> tuple:
    """Return (hash_hex, salt_hex) for the given PIN."""
    if salt is None:
        salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", pin.encode("utf-8"), salt, _ITERATIONS)
    return digest.hex(), salt.hex()


def verify_pin(pin: str, hash_hex: str, salt_hex: str) -> bool:
    if not hash_hex or not salt_hex:
        return False
    salt = bytes.fromhex(salt_hex)
    candidate_hash, _ = hash_pin(pin, salt)
    return hmac.compare_digest(candidate_hash, hash_hex)
