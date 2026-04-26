"""Public API for the auth library shape.

The auth package is structured to be a publishable plug-and-play
library (TREK-56 / EPIC-3 P4.1): consumers reach in through this
top-level namespace or :mod:`blunder_tutor.auth.fastapi` and never
through ``core``, ``storage_sqlite``, ``storage_memory``, ``providers``,
or ``cli``. ``__all__`` is the single source of truth for the public
contract — everything else under ``blunder_tutor.auth.*`` is an
implementation detail and may move between subpackages without notice.

The ``hashers`` submodule is re-bound on the package object so test
fixtures that need to monkeypatch the lazy default hasher don't have
to reach into ``core``.
"""

from blunder_tutor.auth.core import hashers
from blunder_tutor.auth.core.errors import (
    AuthError,
    CorruptCredentialError,
    DuplicateEmailError,
    DuplicateUsernameError,
    InvalidEmailError,
    InvalidInviteCodeError,
    InvalidPasswordError,
    InvalidUsernameError,
    UserCapReachedError,
)
from blunder_tutor.auth.core.hashers import (
    BcryptHasher,
    hash_password,
    verify_password,
)
from blunder_tutor.auth.core.invite import generate_invite_code, verify_invite_code
from blunder_tutor.auth.core.policies import (
    HmacInvitePolicy,
    MaxUsersQuota,
    NoQuota,
    OpenSignup,
)
from blunder_tutor.auth.core.protocols import (
    AuthProvider,
    ErrorCodec,
    IdentityRepo,
    InvitePolicy,
    PasswordHasher,
    QuotaPolicy,
    RateLimiter,
    SessionRepo,
    SetupRepo,
    Storage,
    Transaction,
    UserRepo,
)
from blunder_tutor.auth.core.service import AuthService
from blunder_tutor.auth.core.types import (
    CREDENTIALS_PROVIDER_NAME,
    EMAIL_RE,
    PASSWORD_MAX_BYTES,
    PASSWORD_MIN_LEN,
    USERNAME_RE,
    Email,
    Identity,
    IdentityId,
    InviteCode,
    PasswordHash,
    ProviderName,
    Session,
    SessionToken,
    User,
    UserContext,
    UserId,
    Username,
    ValidationRules,
    is_user_id_shape,
    make_email,
    make_identity_id,
    make_session_token,
    make_user_id,
    make_username,
)
from blunder_tutor.auth.fastapi.middleware import AuthMiddleware, MiddlewareConfig
from blunder_tutor.auth.providers.credentials import CredentialsProvider
from blunder_tutor.auth.storage_memory import InMemoryStorage
from blunder_tutor.auth.storage_sqlite import SqliteStorage
from blunder_tutor.auth.storage_sqlite.db import AuthDb
from blunder_tutor.auth.storage_sqlite.repository import (
    IdentityRepository,
    SessionRepository,
    SetupRepository,
    UserRepository,
)
from blunder_tutor.auth.storage_sqlite.schema import (
    FilePermissionPolicy,
    NoOpFilePermissionPolicy,
    initialize_auth_schema,
)

__all__ = [
    "CREDENTIALS_PROVIDER_NAME",
    "EMAIL_RE",
    "PASSWORD_MAX_BYTES",
    "PASSWORD_MIN_LEN",
    "USERNAME_RE",
    # Errors
    "AuthError",
    "CorruptCredentialError",
    "DuplicateEmailError",
    "DuplicateUsernameError",
    "InvalidEmailError",
    "InvalidInviteCodeError",
    "InvalidPasswordError",
    "InvalidUsernameError",
    "UserCapReachedError",
    # Service + middleware
    "AuthService",
    "AuthMiddleware",
    "MiddlewareConfig",
    # Hashers
    "BcryptHasher",
    "hash_password",
    "hashers",
    "verify_password",
    # Invite
    "generate_invite_code",
    "verify_invite_code",
    # Policies
    "HmacInvitePolicy",
    "MaxUsersQuota",
    "NoQuota",
    "OpenSignup",
    # Protocols
    "AuthProvider",
    "ErrorCodec",
    "FilePermissionPolicy",
    "IdentityRepo",
    "InvitePolicy",
    "NoOpFilePermissionPolicy",
    "PasswordHasher",
    "QuotaPolicy",
    "RateLimiter",
    "SessionRepo",
    "SetupRepo",
    "Storage",
    "Transaction",
    "UserRepo",
    # Providers
    "CredentialsProvider",
    # Storage
    "AuthDb",
    "IdentityRepository",
    "InMemoryStorage",
    "SessionRepository",
    "SetupRepository",
    "SqliteStorage",
    "UserRepository",
    "initialize_auth_schema",
    # Entities
    "Email",
    "Identity",
    "IdentityId",
    "InviteCode",
    "PasswordHash",
    "ProviderName",
    "Session",
    "SessionToken",
    "User",
    "UserContext",
    "UserId",
    "Username",
    "ValidationRules",
    # Helpers
    "is_user_id_shape",
    "make_email",
    "make_identity_id",
    "make_session_token",
    "make_user_id",
    "make_username",
]
