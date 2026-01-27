"""Sync games job implementation.

This module contains the SyncGamesJob class which synchronizes games
from all configured platforms.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from pathlib import Path
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
        data_dir: Path,
        analyze_job: AnalyzeGamesJob | None = None,
    ) -> None:
        """Initialize the sync games job.

        Args:
            job_service: Service for managing job state and events.
            settings_repo: Repository for accessing settings.
            game_repo: Repository for game data.
            data_dir: Base data directory.
            analyze_job: Optional analyze job for auto-analysis after sync.
        """
        self.job_service = job_service
        self.settings_repo = settings_repo
        self.game_repo = game_repo
        self.data_dir = data_dir
        self.analyze_job = analyze_job

    async def execute(self, job_id: str, **kwargs: Any) -> dict[str, Any]:
        """Execute the sync job for all configured platforms.

        This method syncs games for each configured username/platform pair
        and optionally triggers auto-analysis for new games.

        Args:
            job_id: Not used directly since we create per-source jobs.
            **kwargs: Additional arguments (unused).

        Returns:
            Dictionary with total stored and skipped counts.
        """
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

        # Update last sync timestamp
        self.settings_repo.set_setting(
            "last_sync_timestamp", datetime.utcnow().isoformat()
        )

        return {"stored": total_stored, "skipped": total_skipped}

    async def _sync_single_source(
        self, job_id: str, source: str, username: str
    ) -> dict[str, Any]:
        """Sync games from a single source.

        Args:
            job_id: The job ID for this sync operation.
            source: The platform source ('lichess' or 'chesscom').
            username: The username to sync games for.

        Returns:
            Dictionary with stored and skipped counts.
        """
        from functools import partial

        from blunder_tutor.fetchers.chesscom import fetch as fetch_chesscom
        from blunder_tutor.fetchers.lichess import fetch as fetch_lichess

        self.job_service.update_job_status(job_id, "running")

        # Get max games setting
        max_games_str = self.settings_repo.get_setting("sync_max_games")
        max_games = int(max_games_str) if max_games_str else 1000

        # Initialize progress
        self.job_service.update_job_progress(job_id, 0, max_games)

        # Define progress callback
        def update_progress(current: int, total: int) -> None:
            self.job_service.update_job_progress(job_id, current, total)

        # Fetch games (runs in executor to avoid blocking)
        loop = asyncio.get_event_loop()

        if source == "lichess":
            fetch_func = partial(
                fetch_lichess,
                username,
                self.data_dir,
                max_games,
                progress_callback=update_progress,
            )
            stored, skipped = await loop.run_in_executor(None, fetch_func)
        elif source == "chesscom":
            fetch_func = partial(
                fetch_chesscom,
                username,
                self.data_dir,
                max_games,
                progress_callback=update_progress,
            )
            stored, skipped = await loop.run_in_executor(None, fetch_func)
        else:
            raise ValueError(f"Unknown source: {source}")

        # Update final progress
        total_processed = stored + skipped
        self.job_service.update_job_progress(job_id, total_processed, total_processed)

        # Refresh game index cache
        await loop.run_in_executor(None, self.game_repo.refresh_index_cache)

        # Complete sync job BEFORE starting auto-analyze
        self.job_service.complete_job(job_id, {"stored": stored, "skipped": skipped})

        # Check if auto-analyze is enabled
        auto_analyze = self.settings_repo.get_setting("analyze_new_games_automatically")
        if auto_analyze == "true" and stored > 0 and self.analyze_job is not None:
            # Trigger analysis job for new games
            analyze_job_id = self.job_service.create_job(
                job_type="analyze",
                username=username,
                source=source,
                max_games=stored,
            )
            asyncio.create_task(
                self.analyze_job.execute(
                    job_id=analyze_job_id,
                    source=source,
                    username=username,
                )
            )

        return {"stored": stored, "skipped": skipped}
