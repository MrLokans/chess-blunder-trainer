from __future__ import annotations

from blunder_tutor.fetchers import chesscom, lichess

# Kept as a mutable dict because tests use `patch.dict(...)` to swap in
# mocks. Treat as read-only at runtime.
VALIDATORS = {  # noqa: WPS407
    "lichess": lichess.validate_username,
    "chesscom": chesscom.validate_username,
}


async def validate_username(platform: str, username: str) -> bool:
    validator = VALIDATORS.get(platform)
    if validator is None:
        return False
    return await validator(username)
