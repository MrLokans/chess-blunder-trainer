from __future__ import annotations

import sqlite3

import aiosqlite
from fastapi import APIRouter, HTTPException, Response, status

from blunder_tutor.auth.fastapi import UserContextDep
from blunder_tutor.background.jobs.stats_sync import fetch_stats_for_profile
from blunder_tutor.constants import JOB_TYPE_IMPORT
from blunder_tutor.events.event_types import JobExecutionRequestEvent
from blunder_tutor.fetchers import RateLimitError
from blunder_tutor.repositories.profile import (
    ProfileNotFoundError,
    SqliteProfileRepository,
)
from blunder_tutor.repositories.profile_types import Profile
from blunder_tutor.web.api._profile_helpers import (
    apply_patch_identity,
    apply_patch_preferences,
    build_profile_shape,
    ensure_upstream_username_exists,
    finalize_new_profile,
    finalize_patch,
    safe_check_username_existence,
)
from blunder_tutor.web.api._profile_schemas import (
    ProfileCreateRequest,
    ProfileShape,
    ProfilesListResponse,
    ProfileStatsRefreshResponse,
    ProfileSyncDispatchResponse,
    ProfileUpdateRequest,
    ProfileValidateRequest,
    ProfileValidateResponse,
    StatsSnapshotShape,
)
from blunder_tutor.web.dependencies import (
    EventBusDep,
    JobRepoDep,
    JobServiceDep,
    ProfileRepoDep,
)

profiles_router = APIRouter()


def _conflict_409(message: str = "concurrent profile write conflict") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail={"error": "conflict", "message": message},
    )


@profiles_router.post(
    "/api/profiles/validate",
    response_model=ProfileValidateResponse,
    summary="Validate a chess platform username",
    description=(
        "Returns existence + duplicate-tracking + rate-limit signals. "
        "Read-only against external APIs and against the local DB; allowed "
        "in demo mode."
    ),
)
async def validate_profile(
    payload: ProfileValidateRequest,
    repo: ProfileRepoDep,
) -> ProfileValidateResponse:
    username = payload.username.strip()
    if not username:
        return ProfileValidateResponse(
            exists=False,
            already_tracked=False,
            profile_id=None,
            rate_limited=False,
        )

    check = await safe_check_username_existence(payload.platform, username)
    existing = await repo.find_by_platform_username(payload.platform, username)

    return ProfileValidateResponse(
        exists=check.exists,
        already_tracked=existing is not None,
        profile_id=existing.id if existing is not None else None,
        rate_limited=check.rate_limited,
    )


@profiles_router.get(
    "/api/profiles",
    response_model=ProfilesListResponse,
    summary="List tracked profiles",
)
async def list_profiles(
    repo: ProfileRepoDep,
    jobs: JobRepoDep,
) -> ProfilesListResponse:
    profiles = await repo.list_profiles()
    items: list[ProfileShape] = []
    for profile in profiles:
        stats = await repo.list_stats(profile.id)
        last_game_sync_at = await jobs.get_last_completed_sync_at(
            profile.platform, profile.username
        )
        items.append(build_profile_shape(profile, stats, last_game_sync_at))
    return ProfilesListResponse(profiles=items)


@profiles_router.post(
    "/api/profiles",
    response_model=ProfileShape,
    status_code=status.HTTP_201_CREATED,
    summary="Create a tracked profile",
)
async def create_profile(
    payload: ProfileCreateRequest,
    repo: ProfileRepoDep,
) -> ProfileShape:
    username = payload.username.strip()
    if not username:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="username must not be blank",
        )

    # Local duplicate check first — cheap, and avoids hitting the upstream
    # provider for a request we already know we'll reject.
    existing = await repo.find_by_platform_username(payload.platform, username)
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": "already_tracked",
                "profile_id": existing.id,
            },
        )

    await ensure_upstream_username_exists(payload.platform, username)

    try:
        profile = await repo.create(
            payload.platform, username, make_primary=payload.make_primary
        )
    except (sqlite3.IntegrityError, aiosqlite.IntegrityError) as exc:
        # Concurrent create raced this one — partial unique index or
        # `(platform, username)` unique constraint fired. Surface as 409.
        raise _conflict_409(
            "another request created this profile concurrently"
        ) from exc
    return await finalize_new_profile(repo, profile.id)


@profiles_router.patch(
    "/api/profiles/{profile_id}",
    response_model=ProfileShape,
    summary="Update a tracked profile",
    description=(
        "Partial update: any subset of `username`, `is_primary`, "
        "`preferences`. Username changes re-run validation; duplicates → 409. "
        "Non-existent target usernames are accepted (the user may be fixing "
        "a typo on a previously-invalid profile)."
    ),
)
async def update_profile(
    profile_id: int,
    payload: ProfileUpdateRequest,
    repo: ProfileRepoDep,
    jobs: JobRepoDep,
) -> ProfileShape:
    existing = await repo.get(profile_id)
    if existing is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="profile not found",
        )

    try:
        confirmed = await apply_patch_identity(
            repo, profile_id=profile_id, existing=existing, payload=payload
        )
        await apply_patch_preferences(repo, profile_id=profile_id, payload=payload)
    except (sqlite3.IntegrityError, aiosqlite.IntegrityError) as exc:
        raise _conflict_409(
            "another request modified this profile concurrently"
        ) from exc
    return await finalize_patch(
        repo, jobs, profile_id=profile_id, confirmed_existence=confirmed
    )


@profiles_router.post(
    "/api/profiles/{profile_id}/sync",
    response_model=ProfileSyncDispatchResponse,
    summary="Trigger a manual game sync for a profile",
    description=(
        "Dispatches a background `JOB_TYPE_IMPORT` job for the profile "
        "and returns its `job_id`. The UI polls "
        "`/api/import/status/{job_id}` for progress, same shape as the "
        "Bulk Import flow."
    ),
)
async def trigger_profile_sync(
    profile_id: int,
    repo: ProfileRepoDep,
    job_service: JobServiceDep,
    event_bus: EventBusDep,
    user_ctx: UserContextDep,
) -> ProfileSyncDispatchResponse:
    profile = await repo.get(profile_id)
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="profile not found",
        )

    # Manual trigger uses `JOB_TYPE_IMPORT` (backfill semantics, capped by
    # `preferences.sync_max_games` or the global default) rather than
    # `JOB_TYPE_SYNC` (incremental from last sync) — spec choice. The user
    # clicking "Sync Now" gets a fresh pull; the scheduler's auto-sync
    # path uses `JOB_TYPE_SYNC` for incremental fetches.
    job_id = await job_service.create_job(
        job_type=JOB_TYPE_IMPORT,
        username=profile.username,
        source=profile.platform,
    )
    event = JobExecutionRequestEvent.create(
        job_id=job_id,
        job_type=JOB_TYPE_IMPORT,
        user_id=user_ctx.user_id,
        profile_id=profile.id,
    )
    await event_bus.publish(event)
    return ProfileSyncDispatchResponse(job_id=job_id)


@profiles_router.post(
    "/api/profiles/{profile_id}/stats/refresh",
    response_model=ProfileStatsRefreshResponse,
    summary="Synchronously refresh a profile's per-mode stats",
    description=(
        "One cheap upstream HTTP call: fetches per-mode rating + games "
        "count, UPSERTs `profile_stats`, touches `last_validated_at`, "
        "and returns the refreshed snapshot. Returns 429 with "
        "`rate_limited: true` when the upstream provider is rate-limiting "
        "the existence check."
    ),
)
async def refresh_profile_stats(
    profile_id: int,
    repo: ProfileRepoDep,
) -> ProfileStatsRefreshResponse:
    profile = await repo.get(profile_id)
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="profile not found",
        )

    try:
        await _do_stats_refresh(repo, profile)
    except RateLimitError as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={"error": "rate_limited", "rate_limited": True},
        ) from exc

    return await _build_stats_refresh_response(repo, profile_id)


async def _do_stats_refresh(repo: SqliteProfileRepository, profile: Profile) -> None:
    """Fetch + upsert + touch_validated_at — the write path of stats refresh.

    Split from `_build_stats_refresh_response` so the upstream-error window
    (`RateLimitError` → 429) is bounded to the write path and doesn't
    overlap with the post-write read (which can race against a concurrent
    profile delete and surface as 404).
    """
    snapshots = await fetch_stats_for_profile(profile)
    if snapshots:
        await repo.upsert_stats(profile.id, snapshots)
    await repo.touch_validated_at(profile.id)


async def _build_stats_refresh_response(
    repo: SqliteProfileRepository, profile_id: int
) -> ProfileStatsRefreshResponse:
    refreshed = await repo.get(profile_id)
    if refreshed is None:
        # Profile was deleted concurrently with this refresh. Return 404
        # rather than a stale shape — the upserted stats rows are now
        # orphaned (next operation against this profile_id will fail).
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="profile not found",
        )

    stats_rows = await repo.list_stats(profile_id)
    return ProfileStatsRefreshResponse(
        stats=[
            StatsSnapshotShape(
                mode=row.mode,
                rating=row.rating,
                games_count=row.games_count,
                synced_at=row.synced_at,
            )
            for row in stats_rows
        ],
        last_validated_at=refreshed.last_validated_at,
    )


@profiles_router.delete(
    "/api/profiles/{profile_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a tracked profile",
    description=(
        "Required `detach_games` query parameter (`true`|`false`); missing "
        "or invalid → 400. `true` keeps games with `profile_id = NULL`; "
        "`false` hard-deletes the games and their analysis rows. The repo "
        "does NOT auto-promote another profile to primary — call PATCH "
        "explicitly if that's desired."
    ),
)
async def delete_profile(
    profile_id: int,
    repo: ProfileRepoDep,
    detach_games: str | None = None,
) -> Response:
    if detach_games not in {"true", "false"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "detach_games query parameter is required and must be 'true' or 'false'"
            ),
        )
    detach = detach_games == "true"
    try:
        await repo.delete(profile_id, detach_games=detach)
    except ProfileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="profile not found",
        ) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)
