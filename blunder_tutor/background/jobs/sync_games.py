from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, ClassVar

from blunder_tutor.auth import UserId
from blunder_tutor.background.base import BaseJob
from blunder_tutor.background.registry import register_job
from blunder_tutor.constants import JOB_STATUS_FAILED, JOB_TYPE_ANALYZE, JOB_TYPE_SYNC
from blunder_tutor.events import EventBus, JobExecutionRequestEvent
from blunder_tutor.fetchers import chesscom, lichess
from blunder_tutor.repositories.game_repository import GameRepository
from blunder_tutor.repositories.settings import SettingsRepository
from blunder_tutor.services.job_service import JobService

logger = logging.getLogger(__name__)


def _sync_result(stored: int, skipped: int) -> dict[str, int]:
    return {"stored": stored, "skipped": skipped}


@register_job
class SyncGamesJob(BaseJob):
    job_identifier: ClassVar[str] = "sync"

    def __init__(
        self,
        job_service: JobService,
        settings_repo: SettingsRepository,
        game_repo: GameRepository,
        user_id: UserId,
        event_bus: EventBus | None = None,
    ) -> None:
        self.job_service = job_service
        self.settings_repo = settings_repo
        self.game_repo = game_repo
        self.user_id = user_id
        self.event_bus = event_bus

    async def execute(self, job_id: str, **kwargs: Any) -> dict[str, Any]:
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
                result = await self._sync_single_source(source_job_id, source, username)
                total_stored += result.get("stored", 0)
                total_skipped += result.get("skipped", 0)
            except Exception as e:
                logger.error(f"Sync job {source_job_id} failed: {e}")
                await self.job_service.update_job_status(
                    source_job_id, JOB_STATUS_FAILED, str(e)
                )

        await self.settings_repo.write_setting(
            "last_sync_timestamp", datetime.utcnow().isoformat()
        )

        return _sync_result(stored=total_stored, skipped=total_skipped)

    async def _sync_single_source(
        self, job_id: str, source: str, username: str
    ) -> dict[str, Any]:
        await self.job_service.update_job_status(job_id, "running")

        max_games_str = await self.settings_repo.read_setting("sync_max_games")
        max_games = int(max_games_str) if max_games_str else 1000

        # Get the timestamp of the latest game we already have
        since = await self.game_repo.get_latest_game_time(source, username)
        if since:
            logger.info(f"Incremental sync for {source}/{username} since {since}")

        await self.job_service.update_job_progress(job_id, 0, max_games)

        async def update_progress(current: int, total: int) -> None:  # noqa: WPS430 — `progress_callback` closure; captures `self.job_service` and `job_id`.
            await self.job_service.update_job_progress(job_id, current, total)

        if source == "lichess":
            games, _seen_ids = await lichess.fetch(
                username,
                max_games,
                since=since,
                progress_callback=update_progress,
            )
        elif source == "chesscom":
            games, _seen_ids = await chesscom.fetch(
                username,
                max_games,
                since=since,
                progress_callback=update_progress,
            )
        else:
            raise ValueError(f"Unknown source: {source}")

        inserted = await self.game_repo.insert_games(games)
        skipped = len(games) - inserted

        total_processed = len(games)
        await self.job_service.update_job_progress(
            job_id, total_processed, total_processed
        )

        sync_result = _sync_result(stored=inserted, skipped=skipped)
        await self.job_service.complete_job(job_id, sync_result)

        auto_analyze = await self.settings_repo.read_setting(
            "analyze_new_games_automatically"
        )
        if auto_analyze == "true" and inserted > 0 and self.event_bus is not None:
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

        return sync_result
