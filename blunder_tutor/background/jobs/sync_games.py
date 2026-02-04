from __future__ import annotations

import logging
from datetime import datetime
from typing import TYPE_CHECKING, Any, ClassVar

from blunder_tutor.background.base import BaseJob
from blunder_tutor.background.registry import register_job
from blunder_tutor.events import EventBus, JobExecutionRequestEvent

if TYPE_CHECKING:
    from blunder_tutor.repositories.game_repository import GameRepository
    from blunder_tutor.repositories.settings import SettingsRepository
    from blunder_tutor.services.job_service import JobService

logger = logging.getLogger(__name__)


@register_job
class SyncGamesJob(BaseJob):
    job_identifier: ClassVar[str] = "sync"

    def __init__(
        self,
        job_service: JobService,
        settings_repo: SettingsRepository,
        game_repo: GameRepository,
        event_bus: EventBus | None = None,
    ) -> None:
        self.job_service = job_service
        self.settings_repo = settings_repo
        self.game_repo = game_repo
        self.event_bus = event_bus

    async def execute(self, job_id: str, **kwargs: Any) -> dict[str, Any]:
        usernames = await self.settings_repo.get_configured_usernames()

        if not usernames:
            logger.info("No usernames configured for sync")
            return {"stored": 0, "skipped": 0}

        total_stored = 0
        total_skipped = 0

        for source, username in usernames.items():
            source_job_id = await self.job_service.create_job(
                job_type="sync",
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
                    source_job_id, "failed", str(e)
                )

        await self.settings_repo.set_setting(
            "last_sync_timestamp", datetime.utcnow().isoformat()
        )

        return {"stored": total_stored, "skipped": total_skipped}

    async def _sync_single_source(
        self, job_id: str, source: str, username: str
    ) -> dict[str, Any]:
        from blunder_tutor.fetchers import chesscom, lichess

        await self.job_service.update_job_status(job_id, "running")

        max_games_str = await self.settings_repo.get_setting("sync_max_games")
        max_games = int(max_games_str) if max_games_str else 1000

        # Get the timestamp of the latest game we already have
        since = await self.game_repo.get_latest_game_time(source, username)
        if since:
            logger.info(f"Incremental sync for {source}/{username} since {since}")

        await self.job_service.update_job_progress(job_id, 0, max_games)

        async def update_progress(current: int, total: int) -> None:
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

        await self.job_service.complete_job(
            job_id, {"stored": inserted, "skipped": skipped}
        )

        auto_analyze = await self.settings_repo.get_setting(
            "analyze_new_games_automatically"
        )
        if auto_analyze == "true" and inserted > 0 and self.event_bus is not None:
            analyze_job_id = await self.job_service.create_job(
                job_type="analyze",
                username=username,
                source=source,
                max_games=inserted,
            )
            event = JobExecutionRequestEvent.create(
                job_id=analyze_job_id,
                job_type="analyze",
                source=source,
                username=username,
            )
            await self.event_bus.publish(event)

        return {"stored": inserted, "skipped": skipped}
