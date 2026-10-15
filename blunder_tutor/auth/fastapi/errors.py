from __future__ import annotations

from blunder_tutor.auth.core.errors import (
    AuthError,
    DuplicateEmailError,
    DuplicateUsernameError,
    InvalidInviteCodeError,
    InviteCannotBeRegeneratedError,
    NoCredentialsIdentityError,
    UserCapReachedError,
    UserNotFoundError,
    _InputError,
)

_HttpErrorEntry = tuple[type[AuthError], int, str]

_DIRECT_ERROR_MAP: tuple[_HttpErrorEntry, ...] = (
    (UserCapReachedError, 403, "user_cap_reached"),
    (DuplicateUsernameError, 409, "username_taken"),
    (DuplicateEmailError, 409, "email_taken"),
    (UserNotFoundError, 404, "user_not_found"),
    (NoCredentialsIdentityError, 409, "no_credentials_identity"),
    (InviteCannotBeRegeneratedError, 409, "users_already_exist"),
)


class DefaultErrorCodec:
    def to_http(self, exc: AuthError) -> tuple[int, str]:
        for err_type, status, slug in _DIRECT_ERROR_MAP:
            if isinstance(exc, err_type):
                return status, slug
        if isinstance(exc, InvalidInviteCodeError):
            # One status for missing/rotated/not_issued avoids an enumeration oracle;
            # the slug still tells the UI which.
            detail = (
                "invite_code_required"
                if str(exc.offender) == "missing"
                else "invite_code_invalid"
            )
            return 403, detail
        if isinstance(exc, _InputError):
            # `code` is the stable slug on every input-error subclass, so no
            # per-subclass branch.
            return 400, exc.code
        # Unknown subclass surfaces as 500 rather than being swallowed; consumers adding
        # errors override the codec.
        return 500, "internal_error"
