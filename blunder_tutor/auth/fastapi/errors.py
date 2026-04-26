"""HTTP error codec — maps :class:`AuthError` subclasses to ``(status,
detail)`` tuples for the auth API routes.

The default codec ships blunder_tutor's stable detail slugs so the
existing HTTP contract holds for consumers that don't customise.
A consumer wanting i18n keys, different status codes, or a different
detail vocabulary subclasses :class:`DefaultErrorCodec` and overrides
:meth:`to_http`, or supplies a fully custom :class:`ErrorCodec`
implementation to :func:`build_auth_router`.
"""

from __future__ import annotations

from blunder_tutor.auth.core.errors import (
    AuthError,
    DuplicateEmailError,
    DuplicateUsernameError,
    InvalidInviteCodeError,
    UserCapReachedError,
    _InputError,
)


class DefaultErrorCodec:
    """Status + detail mapping that preserves blunder_tutor's API
    contract: ``"username_taken"``, ``"invite_code_invalid"``,
    ``"user_cap_reached"``, etc.

    Override :meth:`to_http` (or compose with another codec by
    delegating in the fall-through branch) to change individual
    mappings without re-implementing the whole table.
    """

    def to_http(self, exc: AuthError) -> tuple[int, str]:
        if isinstance(exc, UserCapReachedError):
            return 403, "user_cap_reached"
        if isinstance(exc, InvalidInviteCodeError):
            # Don't split "missing" / "rotated" / "not_issued" into
            # distinct statuses — a single response shape avoids an
            # enumeration oracle on the invite slot. The slug
            # distinguishes "you forgot to send one" from "the one you
            # sent doesn't match" so the UI can prompt accordingly.
            detail = (
                "invite_code_required"
                if str(exc.offender) == "missing"
                else "invite_code_invalid"
            )
            return 403, detail
        if isinstance(exc, DuplicateUsernameError):
            return 409, "username_taken"
        if isinstance(exc, DuplicateEmailError):
            return 409, "email_taken"
        if isinstance(exc, _InputError):
            # ``code`` is the stable slug on every input-error subclass
            # (``invalid_username``, ``invalid_email``, ``invalid_password``,
            # ``invalid_invite_code``). Routes pass the raw class through
            # so the codec needs no per-subclass branch.
            return 400, exc.code
        # Unknown AuthError subclass — surface as 500 so the router never
        # silently swallows an exception it doesn't understand. A consumer
        # adding a new error class should override the codec to map it.
        return 500, "internal_error"
