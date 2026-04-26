from __future__ import annotations

import re
import secrets
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import NewType

# Errors live in their own module (``core.errors``) so consumers can
# import every recoverable failure mode without dragging in entity
# plumbing; re-exported here so internal callers that need entities
# and errors in one shot keep working with a single import.
from blunder_tutor.auth.core.errors import (  # noqa: F401
    AuthError,
    CorruptCredentialError,
    DuplicateEmailError,
    DuplicateUsernameError,
    InvalidEmailError,
    InvalidInviteCodeError,
    InvalidPasswordError,
    InvalidUsernameError,
    InviteCannotBeRegeneratedError,
    NoCredentialsIdentityError,
    UserCapReachedError,
    UserNotFoundError,
    _InputError,
)

UserId = NewType("UserId", str)
Username = NewType("Username", str)
Email = NewType("Email", str)
SessionToken = NewType("SessionToken", str)
IdentityId = NewType("IdentityId", str)
PasswordHash = NewType("PasswordHash", str)
InviteCode = NewType("InviteCode", str)

# Plain typed-string: the auth core can't enumerate every consumer's
# provider catalogue. A library user adding ``"github"`` or
# ``"saml-corp"`` constructs the value via ``ProviderName(name)`` and
# registers an :class:`AuthProvider` keyed on it; the dispatch table
# in :class:`AuthService` is a plain ``dict[ProviderName, AuthProvider]``
# and grows without service-layer changes.
ProviderName = NewType("ProviderName", str)

# Canonical name for the built-in :class:`CredentialsProvider`. Auth
# core wiring (``AuthService.register``/``signup``) hard-codes this
# because credentials is the only provider whose registration flow
# the service layer owns; OAuth/SAML providers live in consumer code
# and mint their own ``ProviderName`` values via the same constructor.
# Importing the constant rather than passing the bare literal keeps
# call sites type-checker-clean against the ``ProviderName`` NewType.
CREDENTIALS_PROVIDER_NAME = ProviderName("credentials")

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
EMAIL_MAX_LEN = 254  # RFC 5321 hard limit on the entire address.
SESSION_TOKEN_HEX_BYTES = 32  # 32 random bytes = 64 hex chars = 256 bits.


@dataclass(frozen=True)
class ValidationRules:
    """Per-application username/email/password validation policy.

    Default values (:meth:`ValidationRules.default`) match blunder_tutor's
    self-hosted policy — 3-32 char usernames, 8-72 byte passwords
    (bcrypt's hard limit), 254-char email cap. A consumer with different
    requirements (longer usernames for enterprise SSO, argon2 with
    256-byte passwords) constructs a custom :class:`ValidationRules`
    and threads it through the hasher and any direct callers of the
    validation methods.
    """

    username_re: re.Pattern[str]
    email_re: re.Pattern[str]
    password_min: int
    password_max_bytes: int
    email_max_len: int

    @classmethod
    def default(cls) -> ValidationRules:
        return cls(
            username_re=USERNAME_RE,
            email_re=EMAIL_RE,
            password_min=PASSWORD_MIN_LEN,
            password_max_bytes=PASSWORD_MAX_BYTES,
            email_max_len=EMAIL_MAX_LEN,
        )

    def make_username(self, raw: str) -> Username:
        low = raw.strip().lower()
        if not self.username_re.match(low):
            raise InvalidUsernameError(raw)
        return Username(low)

    def make_email(self, raw: str) -> Email:
        low = raw.strip().lower()
        if len(low) > self.email_max_len or not self.email_re.match(low):
            raise InvalidEmailError(raw)
        return Email(low)

    def password_bytes(self, raw: str) -> bytes | None:
        encoded = raw.encode("utf-8")
        if len(encoded) < self.password_min or len(encoded) > self.password_max_bytes:
            return None
        return encoded


_DEFAULT_RULES = ValidationRules.default()


def make_username(raw: str) -> Username:
    return _DEFAULT_RULES.make_username(raw)


def make_email(raw: str) -> Email:
    return _DEFAULT_RULES.make_email(raw)


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
    return SessionToken(secrets.token_hex(SESSION_TOKEN_HEX_BYTES))


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
    session_token: SessionToken | None

    @property
    def is_authenticated(self) -> bool:
        # Synthetic single-user contexts (the web-layer bypass for
        # back-compat installs) carry no session token; every reader
        # must check this property instead of re-implementing
        # ``session_token is not None``.
        return self.session_token is not None
