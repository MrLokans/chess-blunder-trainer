from __future__ import annotations

from pathlib import Path

from fastapi import Request

# App-level per-user cache key for pre-auth / AUTH_MODE=none requests.
# The sentinel matches the `_local` UserContext that AuthMiddleware
# synthesises in none mode, so the two modes share a single keying
# strategy. Single source — every consumer (middleware, snapshot,
# delete-account invalidation) must call `_cache_key`, never reproduce
# the sentinel literal.
_NONE_MODE_CACHE_KEY = "_local"


def _cache_key(request: Request) -> str:
    """Per-user cache key. Preserves none-mode semantics (one key for the
    single legacy user) and isolates credentials-mode users from each
    other so setup/locale/feature caches do not leak across accounts.
    """
    ctx = getattr(request.state, "user_ctx", None)
    if ctx is not None:
        return ctx.user_id
    return _NONE_MODE_CACHE_KEY


def _db_path_for(request: Request) -> Path | None:
    """Return the per-request DB path: the signed-in user's DB when an
    `AuthMiddleware`-populated context is present, otherwise the legacy
    single-user path (AUTH_MODE=none).

    In credentials mode with no context (exempt paths before any user is
    signed in) there is no legitimate DB to hit — return ``None`` and let
    the caller fall back to defaults instead of silently opening the
    un-migrated legacy ``data/main.sqlite3``.
    """
    ctx = getattr(request.state, "user_ctx", None)
    if ctx is not None:
        return ctx.db_path
    if getattr(request.app.state, "auth_mode", "none") == "credentials":
        return None
    return request.app.state.config.data.db_path
