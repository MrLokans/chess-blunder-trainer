"""Auth-domain error hierarchy.

Lives apart from ``types.py`` so consumers building UIs around the
auth flow can import every recoverable failure mode in one shot
without dragging in entity classes / NewType plumbing.
"""

from __future__ import annotations


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
    """Username already in use."""


class DuplicateEmailError(AuthError):
    """Email already in use."""


class UserCapReachedError(AuthError):
    """Tenant has hit its configured user limit."""


class CorruptCredentialError(AuthError):
    """Stored credential hash is malformed — indicates DB corruption,
    not a wrong password attempt."""


class UserNotFoundError(AuthError):
    """No user matches the given username. Raised by admin operations
    that look up a user by name (``reset_password``, ``revoke_sessions``,
    ``delete_user``); the service-layer flows that look up by id use
    ``get_user`` returning ``None`` instead.
    """

    def __init__(self, username: str) -> None:
        super().__init__(f"User not found: {username}")
        self.username = username


class NoCredentialsIdentityError(AuthError):
    """The user exists but has no ``credentials`` identity row, so a
    password reset has nothing to update. Surfaces during admin reset
    on accounts that only signed up via OAuth.
    """

    def __init__(self, username: str) -> None:
        super().__init__(f"User has no credentials identity: {username}")
        self.username = username


class InviteCannotBeRegeneratedError(AuthError):
    """Invite codes are first-user-only — a regenerate attempt with
    existing users would imply a misconfiguration, so the admin
    operation refuses rather than minting a code that the
    first-user-gate would never honour.
    """
