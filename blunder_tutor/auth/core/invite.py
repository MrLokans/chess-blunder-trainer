from __future__ import annotations

import hmac
import secrets
from hashlib import sha256

from blunder_tutor.auth.core.types import InviteCode

# 8 bytes (16 hex chars): enough against forgery, short enough to copy from a log.
_TAG_BYTES = 8
_PAYLOAD_BYTES = 16


def _sign(payload: str, secret_key: str) -> str:
    mac = hmac.new(secret_key.encode("utf-8"), payload.encode("utf-8"), sha256)
    return mac.hexdigest()[: _TAG_BYTES * 2]


def generate_invite_code(secret_key: str) -> InviteCode:
    payload = secrets.token_hex(_PAYLOAD_BYTES)
    return InviteCode(f"{payload}.{_sign(payload, secret_key)}")


def verify_invite_code(code: str, secret_key: str) -> bool:
    parts = code.split(".")
    if len(parts) != 2:
        return False
    payload, sig = parts
    if not payload or not sig:
        return False
    expected = _sign(payload, secret_key)
    # Hex strings are ASCII, so compare_digest is safe and leaks no timing.
    return hmac.compare_digest(sig, expected)
