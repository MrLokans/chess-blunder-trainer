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
    """Return the per-request DB path. The value is set by
    :class:`UserDbPathMiddleware` (web layer), which runs after
    :class:`AuthMiddleware` and routes per-user-id through the resolver
    stored on ``app.state.db_path_resolver``.

    Returns ``None`` when no path was set — the credentials-mode pre-auth
    case (exempt paths before any user is signed in). Callers fall back
    to defaults instead of silently opening the un-migrated legacy DB.
    """
    return getattr(request.state, "user_db_path", None)
