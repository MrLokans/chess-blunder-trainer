from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from blunder_tutor.repositories.settings import SettingsRepository
from blunder_tutor.web.request_helpers import _cache_key, _db_path_for

if TYPE_CHECKING:
    from fastapi import Request


@dataclass(frozen=True, slots=True)
class SettingsSnapshot:
    """Per-request bundle of the three per-user settings values that two
    middleware previously each opened the DB to read. Field is `None` when
    the DB was unavailable (credentials mode pre-auth, or DB initializing);
    callers fall back to defaults.
    """

    setup_completed: bool | None
    locale: str | None
    features: dict[str, bool] | None


_EMPTY = SettingsSnapshot(setup_completed=None, locale=None, features=None)


async def get_settings_snapshot(request: Request) -> SettingsSnapshot:
    """Return the per-request snapshot, materializing on first call.
    Subsequent calls in the same request are O(1) attribute reads.

    Materialization opens the user DB exactly once and populates all three
    per-user caches as a side effect, so the next request for the same
    user can short-circuit at the cache layer without touching this helper.
    """
    cached = getattr(request.state, "settings_snapshot", None)
    if cached is not None:
        return cached

    db_path = _db_path_for(request)
    if db_path is None:
        request.state.settings_snapshot = _EMPTY
        return _EMPTY

    try:
        async with SettingsRepository(db_path=db_path) as repo:
            setup_completed = await repo.is_setup_completed()
            locale = await repo.get_setting("locale")
            features = await repo.get_feature_flags()
    except Exception:
        request.state.settings_snapshot = _EMPTY
        return _EMPTY

    snapshot = SettingsSnapshot(
        setup_completed=setup_completed,
        locale=locale,
        features=features,
    )
    request.state.settings_snapshot = snapshot

    state = request.app.state
    key = _cache_key(request)
    state.setup_completed_cache.set(key, setup_completed)
    if locale:
        state.locale_cache.set(key, locale)
    state.features_cache.set(key, features)
    return snapshot
