from __future__ import annotations


class AuthError(Exception):
    """Base for all auth-domain errors."""


class _InputError(AuthError):
    """Invalid caller input.

    The message is safe to show; the offending value stays on `.offender` for logs.
    `.code` is the stable slug the HTTP layer emits, independent of the message."""

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
    """Stored hash is malformed: DB corruption, not a wrong password."""


class UserNotFoundError(AuthError):
    """Raised by admin operations that look up by username; flows by id return None
    instead."""

    def __init__(self, username: str) -> None:
        super().__init__(f"User not found: {username}")
        self.username = username


class NoCredentialsIdentityError(AuthError):
    """User has no credentials identity (OAuth-only), so there is nothing to reset."""

    def __init__(self, username: str) -> None:
        super().__init__(f"User has no credentials identity: {username}")
        self.username = username


class InviteCannotBeRegeneratedError(AuthError):
    """Raised when regenerating an invite while users exist; the first-user gate would
    never honour it."""
