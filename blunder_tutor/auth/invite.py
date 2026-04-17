from __future__ import annotations

import hmac
import secrets
from hashlib import sha256

from blunder_tutor.auth.types import InviteCode

# HMAC tag length. 8 bytes (16 hex chars) truncation is standard for
# short-form HMAC tags — matches SipHash / AWS sig-v4 patterns. Enough
# entropy to prevent forgery while keeping the code short enough to
# copy-paste from a server log.
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
    # hmac.compare_digest on strings works if both are ASCII; we keep them
    # as hex so it's safe. Returns False deterministically on any length or
    # content mismatch without leaking timing info about which char differs.
    return hmac.compare_digest(sig, expected)
