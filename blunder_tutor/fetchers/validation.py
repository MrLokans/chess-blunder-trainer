from __future__ import annotations

from blunder_tutor.fetchers import ExistenceCheck, chesscom, lichess

# Kept as a mutable dict because tests use `patch.dict(...)` to swap in
# mocks. Treat as read-only at runtime.
VALIDATORS = {  # noqa: WPS407
    "lichess": lichess.validate_username,
    "chesscom": chesscom.validate_username,
}

_EXISTENCE_CHECKERS = {  # noqa: WPS407
    "lichess": lichess.check_username_existence,
    "chesscom": chesscom.check_username_existence,
}


async def validate_username(platform: str, username: str) -> bool:
    validator = VALIDATORS.get(platform)
    if validator is None:
        return False
    return await validator(username)


async def check_username_existence(platform: str, username: str) -> ExistenceCheck:
    """Authoritative existence check: distinguishes 404 from persistent 429.

    Used by `/api/profiles/validate`. Unlike `validate_username` (which
    swallows all errors as `False`), this surfaces rate limits via
    `ExistenceCheck.rate_limited` so the API can communicate "we don't
    know" to the caller.
    """
    checker = _EXISTENCE_CHECKERS.get(platform)
    if checker is None:
        return ExistenceCheck(exists=False, rate_limited=False)
    return await checker(username)
