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
    pass


class DuplicateEmailError(AuthError):
    pass


class UserCapReachedError(AuthError):
    pass


class CorruptCredentialError(AuthError):
    """Stored credential hash is malformed — indicates DB corruption,
    not a wrong password attempt."""
