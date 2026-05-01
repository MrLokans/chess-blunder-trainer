from __future__ import annotations

import httpx
from fastapi import HTTPException, status

from blunder_tutor.fetchers import ExistenceCheck
from blunder_tutor.fetchers.resilience import RetryableHTTPError
from blunder_tutor.fetchers.validation import check_username_existence
from blunder_tutor.repositories.job_repository import JobRepository
from blunder_tutor.repositories.profile import (
    Profile,
    ProfileStatSnapshot,
    SqliteProfileRepository,
)
from blunder_tutor.web.api._profile_schemas import (
    PreferencesPatch,
    PreferencesShape,
    ProfileShape,
    ProfileUpdateRequest,
    StatsSnapshotShape,
)


async def safe_check_username_existence(platform: str, username: str) -> ExistenceCheck:
    """Existence check that maps upstream HTTP errors to a 502.

    Wraps `check_username_existence` so that anything other than 200/404/429
    (e.g. persistent 5xx after retry exhaustion, 4xx like 451) surfaces as
    `HTTPException(502)` rather than a bare 500. Use this in handlers that
    want strict "we know existence" semantics (`validate_profile`,
    `create_profile`). PATCH calls the underlying `check_username_existence`
    directly because it accepts uncertainty.
    """
    try:
        return await check_username_existence(platform, username)
    except RetryableHTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=(
                f"{platform} upstream unavailable "
                f"(status {exc.response.status_code} after retries)"
            ),
        ) from exc
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"{platform} upstream returned {exc.response.status_code}",
        ) from exc


def build_profile_shape(
    profile: Profile,
    stats: list[ProfileStatSnapshot],
    last_game_sync_at: str | None,
) -> ProfileShape:
    # `default=None` covers the case where every snapshot has
    # `synced_at = None` (e.g. demo-mode in-memory seed) — without it, the
    # generator's empty-after-filter raises `ValueError`.
    last_stats_sync_at = max(
        (snap.synced_at for snap in stats if snap.synced_at is not None),
        default=None,
    )
    return ProfileShape(
        id=profile.id,
        platform=profile.platform,
        username=profile.username,
        is_primary=profile.is_primary,
        created_at=profile.created_at,
        last_validated_at=profile.last_validated_at,
        preferences=PreferencesShape(
            auto_sync_enabled=profile.preferences.auto_sync_enabled,
            sync_max_games=profile.preferences.sync_max_games,
        ),
        stats=[
            StatsSnapshotShape(
                mode=snap.mode,
                rating=snap.rating,
                games_count=snap.games_count,
                synced_at=snap.synced_at,
            )
            for snap in stats
        ],
        last_game_sync_at=last_game_sync_at,
        last_stats_sync_at=last_stats_sync_at,
    )


async def ensure_upstream_username_exists(platform: str, username: str) -> None:
    """Raise 502 (upstream error), 503 (rate-limited), or 422 (not found)."""
    check = await safe_check_username_existence(platform, username)
    if check.rate_limited:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(f"{platform} rate-limited the existence check; try again shortly"),
        )
    if not check.exists:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"{platform} user '{username}' not found",
        )


async def validate_username_change(
    repo: SqliteProfileRepository,
    *,
    profile_id: int,
    platform: str,
    new_username: str,
) -> bool:
    """Duplicate + existence checks for a PATCH username change.

    Returns True iff upstream confirmed existence. Raises 409 on duplicate.
    Does NOT raise on non-existent or upstream-unavailable — explicit spec
    judgment so users can fix typos on previously-invalid profiles, even
    when the platform is briefly down.
    """
    other = await repo.find_by_platform_username(platform, new_username)
    # `other.id != profile_id` is defensive: the caller's pre-check already
    # filters self-rename via the lowercased-equality early-out, but this
    # guards against a stale `existing` snapshot under concurrent rename.
    if other is not None and other.id != profile_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": "already_tracked", "profile_id": other.id},
        )
    try:
        check = await check_username_existence(platform, new_username)
    except (RetryableHTTPError, httpx.HTTPStatusError):
        # Accept the change; mark as not-confirmed so caller skips
        # `last_validated_at` refresh.
        return False
    return check.exists and not check.rate_limited


def _preferences_kwargs(prefs: PreferencesPatch) -> dict[str, object]:
    kwargs: dict[str, object] = {}
    fields = prefs.model_fields_set
    if "auto_sync_enabled" in fields:
        kwargs["auto_sync_enabled"] = prefs.auto_sync_enabled
    if "sync_max_games" in fields:
        if prefs.sync_max_games is None:
            kwargs["clear_sync_max_games"] = True
        else:
            kwargs["sync_max_games"] = prefs.sync_max_games
    return kwargs


async def apply_patch_identity(
    repo: SqliteProfileRepository,
    *,
    profile_id: int,
    existing: Profile,
    payload: ProfileUpdateRequest,
) -> bool:
    """Apply username/is_primary changes if requested. Returns True iff the
    upstream existence check confirmed the new username.
    """
    fields = payload.model_fields_set
    confirmed = False
    if "username" in fields and payload.username is not None:
        normalized = payload.username.strip().lower()
        if normalized and normalized != existing.username:
            confirmed = await validate_username_change(
                repo,
                profile_id=profile_id,
                platform=existing.platform,
                new_username=normalized,
            )
    if "username" in fields or "is_primary" in fields:
        await repo.update(
            profile_id,
            username=payload.username if "username" in fields else None,
            is_primary=payload.is_primary if "is_primary" in fields else None,
        )
    return confirmed


async def apply_patch_preferences(
    repo: SqliteProfileRepository,
    *,
    profile_id: int,
    payload: ProfileUpdateRequest,
) -> None:
    if "preferences" not in payload.model_fields_set or payload.preferences is None:
        return
    kwargs = _preferences_kwargs(payload.preferences)
    if kwargs:
        await repo.update_preferences(profile_id, **kwargs)


async def finalize_new_profile(
    repo: SqliteProfileRepository, profile_id: int
) -> ProfileShape:
    """Stamp `last_validated_at` and return the GET-shaped DTO for a freshly
    created profile. Empty stats, null `last_game_sync_at`. Extracted so
    `create_profile` stays under WPS238's raise-count limit.
    """
    await repo.touch_validated_at(profile_id)
    refreshed = await repo.get(profile_id)
    if refreshed is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="profile disappeared after create",
        )
    return build_profile_shape(refreshed, stats=[], last_game_sync_at=None)


async def finalize_patch(
    repo: SqliteProfileRepository,
    jobs: JobRepository,
    *,
    profile_id: int,
    confirmed_existence: bool,
) -> ProfileShape:
    """After PATCH writes complete, refresh `last_validated_at` if the new
    username was upstream-confirmed, then return the full GET-shaped DTO.
    """
    if confirmed_existence:
        await repo.touch_validated_at(profile_id)
    refreshed = await repo.get(profile_id)
    if refreshed is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="profile disappeared after update",
        )
    stats = await repo.list_stats(profile_id)
    last_game_sync_at = await jobs.get_last_completed_sync_at(
        refreshed.platform, refreshed.username
    )
    return build_profile_shape(refreshed, stats, last_game_sync_at)
