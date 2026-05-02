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
    JOB_TYPE_SYNC,
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
_VALID_SOURCES: frozenset[str] = frozenset((PLATFORM_LICHESS, PLATFORM_CHESSCOM))

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
        if profile_id is not None:
            return await self._execute_for_profile(int(profile_id))
        # /api/setup has been removed. The legacy branch below now serves
        # only scheduler dispatches that haven't been migrated to per-profile
        # fan-out (TREK-108) and any remaining /api/sync/start callers.
        # One log per parent dispatch — child sync jobs iterating over
        # (source, username) do not log again. `info` because the legacy
        # path is the expected state during the transition window.
        logger.info(
            f"sync {job_id}: legacy payload without profile_id — "
            f"rows inserted with profile_id=NULL"
        )
        return await self._execute_legacy()

    async def _execute_for_profile(self, profile_id: int) -> dict[str, Any]:
        profile = await self.profile_repo.get(profile_id)
        if profile is None:
            logger.warning(f"sync: profile {profile_id} not found, skipping")
            return _sync_result(stored=0, skipped=0)

        source_job_id = await self.job_service.create_job(
            job_type=JOB_TYPE_SYNC,
            username=profile.username,
            source=profile.platform,
        )
        try:
            result = await self._sync_for_profile(source_job_id, profile)
        except Exception as exc:
            logger.error(f"Sync job {source_job_id} failed: {exc}")
            await self.job_service.update_job_status(
                source_job_id, JOB_STATUS_FAILED, str(exc)
            )
            raise

        await self._touch_last_sync_timestamp()
        return result

    # TREK-7.X (Epic 3 setup rewrite): _execute_legacy and its
    # _sync_legacy_source helper are the legacy username-pair entry-point.
    # Delete both when the scheduler fan-out (TREK-108) always provides a
    # profile_id and `settings_repo.get_configured_usernames` no longer
    # has callers. Rows inserted by this branch get profile_id=NULL; the
    # Epic 3 cleanup migration backfills them by (source, username) match.
    async def _execute_legacy(self) -> dict[str, Any]:
        usernames = await self.settings_repo.get_configured_usernames()

        if not usernames:
            logger.info("No usernames configured for sync")
            return _sync_result(stored=0, skipped=0)

        total_stored = 0
        total_skipped = 0

        for source, username in usernames.items():
            source_job_id = await self.job_service.create_job(
                job_type=JOB_TYPE_SYNC,
                username=username,
                source=source,
            )

            try:
                result = await self._sync_legacy_source(source_job_id, source, username)
                total_stored += result.get("stored", 0)
                total_skipped += result.get("skipped", 0)
            except Exception as exc:
                logger.error(f"Sync job {source_job_id} failed: {exc}")
                await self.job_service.update_job_status(
                    source_job_id, JOB_STATUS_FAILED, str(exc)
                )

        await self._touch_last_sync_timestamp()
        return _sync_result(stored=total_stored, skipped=total_skipped)

    async def _sync_for_profile(self, job_id: str, profile: Profile) -> dict[str, Any]:
        if profile.platform not in _VALID_SOURCES:
            raise ValueError(f"Unknown source: {profile.platform}")
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

    async def _sync_legacy_source(
        self, job_id: str, source: str, username: str
    ) -> dict[str, Any]:
        if source not in _VALID_SOURCES:
            raise ValueError(f"Unknown source: {source}")

        max_games = await self._resolve_global_max_games()
        since = await self.game_repo.get_latest_game_time(source, username)
        if since:
            logger.info(f"Incremental sync for {source}/{username} since {since}")

        sync_result = await self.job_service.run_with_lifecycle(
            job_id,
            max_games,
            lambda progress: self._fetch_and_store(
                source, username, max_games, since, progress
            ),
        )
        await self._maybe_trigger_auto_analysis(
            source, username, int(sync_result["stored"])
        )
        return sync_result

    async def _resolve_global_max_games(self) -> int:
        max_games_str = await self.settings_repo.read_setting("sync_max_games")
        return int(max_games_str) if max_games_str else _DEFAULT_MAX_GAMES

    async def _resolve_max_games_for_profile(self, profile: Profile) -> int:
        per_profile = profile.preferences.sync_max_games
        if per_profile is not None:
            return per_profile
        return await self._resolve_global_max_games()

    # TREK-7.X (Epic 3 setup rewrite): post-TREK-108 the scheduler reads
    # per-profile timestamps from `background_jobs.completed_at`, not this
    # setting. No production reader remains (verified via grep before
    # marking; `/api/sync/status` queries `JOB_TYPE_SYNC` rows directly).
    # Delete this method and its two call sites with the legacy path
    # cleanup.
    async def _touch_last_sync_timestamp(self) -> None:
        await self.settings_repo.write_setting(
            "last_sync_timestamp", datetime.utcnow().isoformat()
        )

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
