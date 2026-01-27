"""Sync games job implementation.

This module contains the SyncGamesJob class which synchronizes games
from all configured platforms.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import TYPE_CHECKING, Any, ClassVar

from blunder_tutor.background.base import BaseJob
from blunder_tutor.background.registry import register_job

if TYPE_CHECKING:
    from blunder_tutor.background.jobs.analyze_games import AnalyzeGamesJob
    from blunder_tutor.repositories.game_repository import GameRepository
    from blunder_tutor.repositories.settings import SettingsRepository
    from blunder_tutor.services.job_service import JobService

logger = logging.getLogger(__name__)


@register_job
class SyncGamesJob(BaseJob):
    """Job for synchronizing games from all configured platforms."""

    job_identifier: ClassVar[str] = "sync"

    def __init__(
        self,
        job_service: JobService,
        settings_repo: SettingsRepository,
        game_repo: GameRepository,
        analyze_job: AnalyzeGamesJob | None = None,
    ) -> None:
        self.job_service = job_service
        self.settings_repo = settings_repo
        self.game_repo = game_repo
        self.analyze_job = analyze_job

    async def execute(self, job_id: str, **kwargs: Any) -> dict[str, Any]:
        usernames = self.settings_repo.get_configured_usernames()

        if not usernames:
            logger.info("No usernames configured for sync")
            return {"stored": 0, "skipped": 0}

        total_stored = 0
        total_skipped = 0

        for source, username in usernames.items():
            source_job_id = self.job_service.create_job(
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
                self.job_service.update_job_status(source_job_id, "failed", str(e))

        self.settings_repo.set_setting(
            "last_sync_timestamp", datetime.utcnow().isoformat()
        )

        return {"stored": total_stored, "skipped": total_skipped}

    async def _sync_single_source(
        self, job_id: str, source: str, username: str
    ) -> dict[str, Any]:
        from functools import partial

        from blunder_tutor.fetchers.chesscom import fetch as fetch_chesscom
        from blunder_tutor.fetchers.lichess import fetch as fetch_lichess

        self.job_service.update_job_status(job_id, "running")

        max_games_str = self.settings_repo.get_setting("sync_max_games")
        max_games = int(max_games_str) if max_games_str else 1000

        self.job_service.update_job_progress(job_id, 0, max_games)

        def update_progress(current: int, total: int) -> None:
            self.job_service.update_job_progress(job_id, current, total)

        loop = asyncio.get_event_loop()

        if source == "lichess":
            fetch_func = partial(
                fetch_lichess,
                username,
                max_games,
                progress_callback=update_progress,
            )
            games, _seen_ids = await loop.run_in_executor(None, fetch_func)
        elif source == "chesscom":
            fetch_func = partial(
                fetch_chesscom,
                username,
                max_games,
                progress_callback=update_progress,
            )
            games, _seen_ids = await loop.run_in_executor(None, fetch_func)
        else:
            raise ValueError(f"Unknown source: {source}")

        inserted = await loop.run_in_executor(None, self.game_repo.insert_games, games)
        skipped = len(games) - inserted

        total_processed = len(games)
        self.job_service.update_job_progress(job_id, total_processed, total_processed)

        self.job_service.complete_job(job_id, {"stored": inserted, "skipped": skipped})

        auto_analyze = self.settings_repo.get_setting("analyze_new_games_automatically")
        if auto_analyze == "true" and inserted > 0 and self.analyze_job is not None:
            analyze_job_id = self.job_service.create_job(
                job_type="analyze",
                username=username,
                source=source,
                max_games=inserted,
            )
            asyncio.create_task(
                self.analyze_job.execute(
                    job_id=analyze_job_id,
                    source=source,
                    username=username,
                )
            )

        return {"stored": inserted, "skipped": skipped}
