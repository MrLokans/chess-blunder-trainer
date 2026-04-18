from __future__ import annotations

import re
import secrets
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Literal, NewType

import bcrypt

UserId = NewType("UserId", str)
Username = NewType("Username", str)
Email = NewType("Email", str)
SessionToken = NewType("SessionToken", str)
IdentityId = NewType("IdentityId", str)
PasswordHash = NewType("PasswordHash", str)
InviteCode = NewType("InviteCode", str)

ProviderName = Literal["credentials", "lichess", "google"]

USERNAME_RE = re.compile(r"^[a-z0-9_\-]{3,32}$")

# Local part and each domain label must be non-empty (no consecutive dots,
# no leading/trailing dots) and the domain must have at least two labels.
# Intentionally stricter than RFC 5322 — we don't need to accept quoted locals
# or bracketed IP-literal domains, and rejecting "a..b@x.com" / "a@.b.com"
# prevents DB unique-constraint duplicates that confuse support.
_EMAIL_LABEL = r"[^\s@.]+"
EMAIL_RE = re.compile(
    rf"^{_EMAIL_LABEL}(?:\.{_EMAIL_LABEL})*@{_EMAIL_LABEL}(?:\.{_EMAIL_LABEL})+$"
)

PASSWORD_MIN_LEN = 8
PASSWORD_MAX_BYTES = 72  # bcrypt hard limit — enforced in bytes, not chars


class AuthError(Exception):
    """Base for all auth-domain errors."""


class _InputError(AuthError):
    """Invalid input from the caller. Error message is safe to surface;
    the offending value is kept on `.offender` for logs only. `.code` is
    the stable slug the HTTP layer emits — intentionally divorced from
    the human-readable message so translations and renamed error strings
    can't desync.
    """

    _message: str = "invalid input"
    code: str = "invalid_input"

    def __init__(self, offender: str = "") -> None:
        super().__init__(self._message)
        self.offender = offender


class InvalidUsernameError(_InputError):
    _message = "invalid username"
    code = "invalid_username"


class InvalidEmailError(_InputError):
    _message = "invalid email"
    code = "invalid_email"


class InvalidPasswordError(_InputError):
    _message = "invalid password"
    code = "invalid_password"


class InvalidInviteCodeError(_InputError):
    _message = "invalid invite code"
    code = "invalid_invite_code"


class DuplicateUsernameError(AuthError):
    pass


class DuplicateEmailError(AuthError):
    pass


class UserCapReachedError(AuthError):
    pass


class CorruptCredentialError(AuthError):
    """Stored credential hash is malformed — indicates DB corruption,
    not a wrong password attempt."""


def make_username(raw: str) -> Username:
    low = raw.strip().lower()
    if not USERNAME_RE.match(low):
        raise InvalidUsernameError(raw)
    return Username(low)


def make_email(raw: str) -> Email:
    low = raw.strip().lower()
    if len(low) > 254 or not EMAIL_RE.match(low):
        raise InvalidEmailError(raw)
    return Email(low)


_USER_ID_RE = re.compile(r"^[0-9a-f]{32}$")


def make_user_id() -> UserId:
    return UserId(uuid.uuid4().hex)


def is_user_id_shape(candidate: str) -> bool:
    """True iff ``candidate`` could plausibly be a ``UserId`` (32-char
    lowercase hex). Used by orphan-directory scans to distinguish
    per-user data dirs from operator artefacts like ``users/backups``
    or ``users/README`` before any destructive action.
    """
    return bool(_USER_ID_RE.match(candidate))


def make_identity_id() -> IdentityId:
    return IdentityId(uuid.uuid4().hex)


def make_session_token() -> SessionToken:
    return SessionToken(secrets.token_hex(32))


def _password_bytes(raw: str) -> bytes | None:
    encoded = raw.encode("utf-8")
    if len(encoded) < PASSWORD_MIN_LEN or len(encoded) > PASSWORD_MAX_BYTES:
        return None
    return encoded


def hash_password(raw: str) -> PasswordHash:
    encoded = _password_bytes(raw)
    if encoded is None:
        raise InvalidPasswordError()
    hashed = bcrypt.hashpw(encoded, bcrypt.gensalt())
    return PasswordHash(hashed.decode("utf-8"))


def verify_password(raw: str, hashed: PasswordHash) -> bool:
    encoded = _password_bytes(raw)
    if encoded is None:
        return False
    try:
        return bcrypt.checkpw(encoded, hashed.encode("utf-8"))
    except ValueError as exc:
        # Structural bcrypt failure (malformed stored hash, wrong prefix, etc.)
        # is a different failure mode than "wrong password" — surface it so
        # corrupted credential rows don't masquerade as auth misses.
        raise CorruptCredentialError(str(exc)) from exc


# Datetime fields on every entity are tz-aware UTC. Repositories are
# responsible for parsing stored ISO timestamps as UTC when hydrating.


@dataclass(frozen=True, slots=True, kw_only=True)
class User:
    id: UserId
    username: Username
    email: Email | None
    created_at: datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class Identity:
    id: IdentityId
    user_id: UserId
    provider: ProviderName
    provider_subject: str
    credential: PasswordHash | None
    created_at: datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class Session:
    token: SessionToken
    user_id: UserId
    created_at: datetime
    expires_at: datetime
    last_seen_at: datetime
    user_agent: str | None
    ip_address: str | None


@dataclass(frozen=True, slots=True, kw_only=True)
class UserContext:
    user_id: UserId
    username: Username
    # Filesystem path is the SaaS seam: a future shared-DB port replaces
    # this with a tenant-id and the `get_db_path` dependency becomes the
    # single swap point.
    db_path: Path
    session_token: SessionToken | None

    @property
    def is_authenticated(self) -> bool:
        # The AUTH_MODE=none middleware synthesizes a `_local` context
        # with no session token; every other code path must check this
        # instead of re-implementing `session_token is not None`.
        return self.session_token is not None
