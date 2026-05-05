from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, ClassVar

from blunder_tutor.auth import UserId
from blunder_tutor.background.base import BaseJob
from blunder_tutor.background.registry import register_job
from blunder_tutor.constants import (
    JOB_STATUS_FAILED,
    JOB_TYPE_ANALYZE,
    PLATFORM_CHESSCOM,
    PLATFORM_LICHESS,
)
from blunder_tutor.events.event_bus import EventBus
from blunder_tutor.events.event_types import JobExecutionRequestEvent
from blunder_tutor.fetchers import chesscom, lichess
from blunder_tutor.repositories.game_repository import GameRepository
from blunder_tutor.repositories.profile import SqliteProfileRepository
from blunder_tutor.repositories.profile_types import Profile
from blunder_tutor.repositories.settings import SettingsRepository
from blunder_tutor.services.job_service import JobService, ProgressCallback

logger = logging.getLogger(__name__)

_DEFAULT_MAX_GAMES = 1000

GameRow = dict[str, object]
FetchResult = tuple[list[GameRow], Any]


def _sync_result(stored: int, skipped: int) -> dict[str, int]:
    return {"stored": stored, "skipped": skipped}  # noqa: WPS226 — dict keys are the job-result API contract.


async def _fetch_games(
    source: str,
    username: str,
    max_games: int,
    *,
    since: datetime | None,
    progress_callback: Any,
) -> FetchResult:
    """Dynamic dispatch over fetcher modules — see import_games.py for why."""
    if source == PLATFORM_LICHESS:
        return await lichess.fetch(
            username,
            max_games,
            since=since,
            progress_callback=progress_callback,
        )
    if source == PLATFORM_CHESSCOM:
        return await chesscom.fetch(
            username,
            max_games,
            since=since,
            progress_callback=progress_callback,
        )
    raise ValueError(f"Unknown source: {source}")


@register_job
class SyncGamesJob(BaseJob):
    job_identifier: ClassVar[str] = "sync"

    def __init__(  # noqa: WPS211 — DI surface; each repo is a separate dependency.
        self,
        job_service: JobService,
        settings_repo: SettingsRepository,
        game_repo: GameRepository,
        profile_repo: SqliteProfileRepository,
        user_id: UserId,
        event_bus: EventBus | None = None,
    ) -> None:
        self.job_service = job_service
        self.settings_repo = settings_repo
        self.game_repo = game_repo
        self.profile_repo = profile_repo
        self.user_id = user_id
        self.event_bus = event_bus

    async def execute(self, job_id: str, **kwargs: Any) -> dict[str, Any]:
        profile_id = kwargs.get("profile_id")
        if profile_id is None:
            # All live dispatchers (scheduler, /api/profiles/{id}/sync) pass
            # profile_id. An event arriving without one is either a stale
            # in-flight event from before deploy or a misconfigured caller —
            # flip the parent to FAILED before raising so it cannot orphan
            # at PENDING.
            await self.job_service.update_job_status(
                job_id, JOB_STATUS_FAILED, "sync requires profile_id"
            )
            raise ValueError(f"sync {job_id} dispatched without profile_id")
        return await self._execute_for_profile(job_id, int(profile_id))

    async def _execute_for_profile(
        self, job_id: str, profile_id: int
    ) -> dict[str, Any]:
        profile = await self.profile_repo.get(profile_id)
        if profile is None:
            logger.warning(f"sync {job_id}: profile {profile_id} not found, skipping")
            result = _sync_result(stored=0, skipped=0)
            await self.job_service.complete_job(job_id, result)
            return result
        return await self._sync_for_profile(job_id, profile)

    async def _sync_for_profile(self, job_id: str, profile: Profile) -> dict[str, Any]:
        # Platform validation lives inside `_fetch_games` (called via the
        # lambda below) so a bad platform raises *inside* the lifecycle and
        # `run_with_lifecycle` flips the parent job to FAILED. A pre-flight
        # check here would orphan the parent at PENDING — same shape as the
        # bug fixed alongside this method.
        max_games = await self._resolve_max_games_for_profile(profile)
        since = await self.game_repo.get_latest_game_time(
            profile.platform, profile.username
        )
        if since:
            logger.info(
                f"Incremental sync for {profile.platform}/{profile.username} since {since}"
            )

        sync_result = await self.job_service.run_with_lifecycle(
            job_id,
            max_games,
            lambda progress: self._fetch_and_store(
                profile.platform,
                profile.username,
                max_games,
                since,
                progress,
                profile_id=profile.id,
            ),
        )
        await self._maybe_trigger_auto_analysis(
            profile.platform,
            profile.username,
            int(sync_result["stored"]),
        )
        return sync_result

    async def _resolve_max_games_for_profile(self, profile: Profile) -> int:
        per_profile = profile.preferences.sync_max_games
        if per_profile is not None:
            return per_profile
        max_games_str = await self.settings_repo.read_setting("sync_max_games")
        return int(max_games_str) if max_games_str else _DEFAULT_MAX_GAMES

    async def _fetch_and_store(  # noqa: WPS211 — explicit parameters keep the call-site readable.
        self,
        source: str,
        username: str,
        max_games: int,
        since: datetime | None,
        progress: ProgressCallback,
        *,
        profile_id: int | None = None,
    ) -> dict[str, Any]:
        async def fetcher_progress(current: int, _total: int) -> None:  # noqa: WPS430 — fetcher's (current, total) signature → our progress(int) shape.
            await progress(current)

        games, _ = await _fetch_games(
            source,
            username,
            max_games,
            since=since,
            progress_callback=fetcher_progress,
        )
        inserted = await self.game_repo.insert_games(games, profile_id=profile_id)
        await progress(len(games))
        return _sync_result(stored=inserted, skipped=len(games) - inserted)

    async def _maybe_trigger_auto_analysis(
        self,
        source: str,
        username: str,
        inserted: int,
    ) -> None:
        if inserted <= 0 or self.event_bus is None:
            return
        auto_analyze = await self.settings_repo.read_setting(
            "analyze_new_games_automatically",
        )
        if auto_analyze != "true":
            return
        analyze_job_id = await self.job_service.create_job(
            job_type=JOB_TYPE_ANALYZE,
            username=username,
            source=source,
            max_games=inserted,
        )
        event = JobExecutionRequestEvent.create(
            job_id=analyze_job_id,
            job_type=JOB_TYPE_ANALYZE,
            user_id=self.user_id,
            source=source,
            username=username,
        )
        await self.event_bus.publish(event)
