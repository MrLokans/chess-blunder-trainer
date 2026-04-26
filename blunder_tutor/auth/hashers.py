from __future__ import annotations

import bcrypt

from blunder_tutor.auth.types import (
    CorruptCredentialError,
    InvalidPasswordError,
    PasswordHash,
    ValidationRules,
)

_DUMMY_RAW = b"dummy-password-for-timing-equalization"


class BcryptHasher:
    """Bcrypt-backed password hasher.

    Construction is cheap; the constant-time dummy hash used by
    :class:`CredentialsProvider` is computed lazily on the first call
    to :meth:`dummy_hash`. :class:`AuthService` warms it at startup so
    the first authenticate request never pays the bcrypt cost on a
    cold cache.

    The hasher delegates length validation to its
    :class:`ValidationRules` so the consumer's password policy
    (min length, max bytes — bcrypt caps at 72) is the single source
    of truth.
    """

    def __init__(self, rules: ValidationRules) -> None:
        self._rules = rules
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
            # Structural bcrypt failure (malformed stored hash, wrong
            # prefix, etc.) is different from "wrong password" —
            # surface as :class:`CorruptCredentialError` so corrupted
            # rows don't masquerade as auth misses.
            raise CorruptCredentialError(str(exc)) from exc

    def dummy_hash(self) -> PasswordHash:
        if self._dummy is None:
            self._dummy = self._hash_unchecked(_DUMMY_RAW)
        return self._dummy

    @staticmethod
    def _hash_unchecked(encoded: bytes) -> PasswordHash:
        hashed = bcrypt.hashpw(encoded, bcrypt.gensalt())
        return PasswordHash(hashed.decode("utf-8"))


# Module-level singleton + shims for callers (CLI admin commands, the
# auth.types module's tests) that just need a default-policy hash or
# verify without instantiating the class. Lazy so importing the
# module doesn't cost a bcrypt round (the hasher itself is cheap to
# construct; only the dummy is).
_default_hasher: BcryptHasher | None = None


def _get_default_hasher() -> BcryptHasher:
    global _default_hasher
    if _default_hasher is None:
        _default_hasher = BcryptHasher(ValidationRules.default())
    return _default_hasher


def hash_password(raw: str) -> PasswordHash:
    return _get_default_hasher().hash(raw)


def verify_password(raw: str, hashed: PasswordHash) -> bool:
    return _get_default_hasher().verify(raw, hashed)
