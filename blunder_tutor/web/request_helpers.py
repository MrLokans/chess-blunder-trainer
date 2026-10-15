from __future__ import annotations

from pathlib import Path

from fastapi import Request

from blunder_tutor.web.bypass_auth import LOCAL_USER_ID

# Reuses the bypass user's `_local` id so both modes share one key; consumers must call
# `_cache_key`, never the literal.
_NONE_MODE_CACHE_KEY = LOCAL_USER_ID


def _cache_key(request: Request) -> str:
    ctx = getattr(request.state, "user_ctx", None)
    if ctx is not None:
        return ctx.user_id
    return _NONE_MODE_CACHE_KEY


def _db_path_for(request: Request) -> Path | None:
    """None on pre-auth exempt paths so callers use defaults instead of opening an
    un-migrated DB."""
    return getattr(request.state, "user_db_path", None)
