"""Cheap stats-only sync job.

Fire-and-forget by design: dispatched by the scheduler via
`JobExecutionRequestEvent` *without* a `job_service.create_job` row, so
there is no `background_jobs` lifecycle to advance — the runner directly
UPSERTs `profile_stats` and updates `profile.last_validated_at`. Adding a
job row in the future also means adding `update_job_status` calls here.
"""

from __future__ import annotations

import logging
from typing import Any, ClassVar

from blunder_tutor.background.base import BaseJob
from blunder_tutor.background.registry import register_job
from blunder_tutor.constants import PLATFORM_CHESSCOM, PLATFORM_LICHESS
from blunder_tutor.fetchers import RateLimitError, chesscom, lichess
from blunder_tutor.repositories.profile import (
    ProfileStatSnapshot,
    SqliteProfileRepository,
)
from blunder_tutor.repositories.profile_types import Profile

logger = logging.getLogger(__name__)


async def fetch_stats_for_profile(profile: Profile) -> list[ProfileStatSnapshot]:
    """Dispatch to the appropriate fetcher for the profile's platform.

    Looked up dynamically rather than via a module-level dict so tests can
    `monkeypatch.setattr` the underlying fetcher modules — a captured
    reference would shadow the patch.

    Public (no leading underscore) because the synchronous
    `POST /api/profiles/{id}/stats/refresh` endpoint reuses the same
    dispatch.

    TREK-127 follow-up: when `dispatch_fetch` lands in
    `blunder_tutor/fetchers/__init__.py`, move this helper there and
    re-import from both `stats_sync.py` and `web/api/profiles.py`.
    Platform-keyed dispatch belongs in the fetchers package, not in a
    job module.
    """
    if profile.platform == PLATFORM_LICHESS:
        return await lichess.fetch_user_perfs(profile.username)
    if profile.platform == PLATFORM_CHESSCOM:
        return await chesscom.fetch_user_stats(profile.username)
    raise ValueError(f"unknown platform: {profile.platform!r}")


def _result(
    *, stored: int, deferred: bool = False, missing: bool = False
) -> dict[str, Any]:
    payload: dict[str, Any] = {"deferred": deferred, "stored": stored}
    if missing:
        payload["missing"] = True
    return payload


@register_job
class StatsSyncJob(BaseJob):
    job_identifier: ClassVar[str] = "stats_sync"

    def __init__(self, profile_repo: SqliteProfileRepository) -> None:
        self.profile_repo = profile_repo

    async def execute(self, job_id: str, **kwargs: Any) -> dict[str, Any]:
        # `profile_id` is required: stats_sync is dispatched only by the
        # scheduler / manual triggers, which always supply it. KeyError
        # here is the load-bearing failure mode for a misconfigured caller.
        profile_id = int(kwargs["profile_id"])
        profile = await self.profile_repo.get(profile_id)
        if profile is None:
            logger.info(
                f"stats_sync {job_id}: profile {profile_id} not found, skipping"
            )
            return _result(stored=0, missing=True)

        try:
            snapshots = await fetch_stats_for_profile(profile)
        except RateLimitError:
            logger.info(
                f"stats_sync {job_id}: {profile.platform} rate-limited "
                f"profile {profile_id}, deferring to next tick"
            )
            return _result(stored=0, deferred=True)
        except ValueError:
            logger.warning(
                f"stats_sync {job_id}: unknown platform {profile.platform!r} "
                f"for profile {profile_id}"
            )
            return _result(stored=0)

        if snapshots:
            await self.profile_repo.upsert_stats(profile_id, snapshots)
        await self.profile_repo.touch_validated_at(profile_id)
        return _result(stored=len(snapshots))
