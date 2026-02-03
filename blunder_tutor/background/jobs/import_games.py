from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, ClassVar

from blunder_tutor.background.base import BaseJob
from blunder_tutor.background.registry import register_job
from blunder_tutor.events import EventBus, JobExecutionRequestEvent
from blunder_tutor.fetchers import chesscom, lichess

if TYPE_CHECKING:
    from blunder_tutor.repositories.game_repository import GameRepository
    from blunder_tutor.repositories.settings import SettingsRepository
    from blunder_tutor.services.job_service import JobService

logger = logging.getLogger(__name__)


@register_job
class ImportGamesJob(BaseJob):
    job_identifier: ClassVar[str] = "import"

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
        source = kwargs.get("source")
        username = kwargs.get("username")

        if not source:
            raise ValueError("source is required")
        if not username:
            raise ValueError("username is required")

        max_games = kwargs.get("max_games")
        if max_games is None:
            max_games_str = await self.settings_repo.get_setting("sync_max_games")
            max_games = int(max_games_str) if max_games_str else 1000

        await self.job_service.update_job_status(job_id, "running")
        await self.job_service.update_job_progress(job_id, 0, max_games)

        async def update_progress(current: int, total: int) -> None:
            await self.job_service.update_job_progress(job_id, current, total)

        try:
            if source == "lichess":
                games, _seen_ids = await lichess.fetch(
                    username,
                    max_games,
                    progress_callback=update_progress,
                )
            elif source == "chesscom":
                games, _seen_ids = await chesscom.fetch(
                    username,
                    max_games,
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

            result = {"stored": inserted, "skipped": skipped}
            await self.job_service.complete_job(job_id, result)

            # Trigger auto-analysis if enabled and games were imported
            await self._trigger_auto_analysis(source, username, inserted)

            return result

        except Exception as e:
            logger.error(f"Error in import job {job_id}: {e}")
            await self.job_service.update_job_status(job_id, "failed", str(e))
            raise

    async def _trigger_auto_analysis(
        self, source: str, username: str, inserted: int
    ) -> None:
        if inserted <= 0 or self.event_bus is None:
            return

        auto_analyze = await self.settings_repo.get_setting(
            "analyze_new_games_automatically"
        )
        if auto_analyze != "true":
            return

        logger.info(f"Auto-triggering analysis for {inserted} new games")

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
