from __future__ import annotations

import bcrypt

from blunder_tutor.auth.core.types import (
    CorruptCredentialError,
    InvalidPasswordError,
    PasswordHash,
    ValidationRules,
)

_DUMMY_RAW = b"dummy-password-for-timing-equalization"


class BcryptHasher:
    """`cost=None` uses the library default; tests lower it. The constant-time dummy hash
    is computed lazily and warmed by `AuthService` at startup."""

    def __init__(self, rules: ValidationRules, *, cost: int | None = None) -> None:
        self._rules = rules
        self._cost = cost
        self._dummy: PasswordHash | None = None

    def hash(self, raw: str) -> PasswordHash:
        encoded = self._rules.password_bytes(raw)
        if encoded is None:
            raise InvalidPasswordError()
        return self._hash_unchecked(encoded)

    def verify(self, raw: str, hashed: PasswordHash) -> bool:
        encoded = self._rules.password_bytes(raw)
        if encoded is None:
            return False
        try:
            return bcrypt.checkpw(encoded, hashed.encode("utf-8"))
        except ValueError as exc:
            # A malformed hash is DB corruption, not a wrong password; surface it
            # distinctly.
            raise CorruptCredentialError(str(exc)) from exc

    def dummy_hash(self) -> PasswordHash:
        if self._dummy is None:
            self._dummy = self._hash_unchecked(_DUMMY_RAW)
        return self._dummy

    def _hash_unchecked(self, encoded: bytes) -> PasswordHash:
        salt = bcrypt.gensalt() if self._cost is None else bcrypt.gensalt(self._cost)
        hashed = bcrypt.hashpw(encoded, salt)
        return PasswordHash(hashed.decode("utf-8"))


# Default-policy shims for callers without a hasher; lazy so importing costs no bcrypt
# round.
cached_hasher: BcryptHasher | None = None


def _get_cached_hasher() -> BcryptHasher:
    global cached_hasher  # noqa: PLW0603 — intentional module-level singleton: lazy-init the dummy hasher used by timing-equalization in `verify_password` before the per-process default exists.
    if cached_hasher is None:
        cached_hasher = BcryptHasher(ValidationRules.default())
    return cached_hasher


def hash_password(raw: str) -> PasswordHash:
    return _get_cached_hasher().hash(raw)


def verify_password(raw: str, hashed: PasswordHash) -> bool:
    return _get_cached_hasher().verify(raw, hashed)
