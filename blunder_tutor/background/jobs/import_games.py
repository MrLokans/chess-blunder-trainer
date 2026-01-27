"""Import games job implementation.

This module contains the ImportGamesJob class which imports games
from a single platform source.
"""

from __future__ import annotations

import asyncio
import logging
from functools import partial
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar

from blunder_tutor.background.base import BaseJob
from blunder_tutor.background.registry import register_job

if TYPE_CHECKING:
    from blunder_tutor.repositories.game_repository import GameRepository
    from blunder_tutor.repositories.settings import SettingsRepository
    from blunder_tutor.services.job_service import JobService

logger = logging.getLogger(__name__)


@register_job
class ImportGamesJob(BaseJob):
    """Job for importing games from a single platform source."""

    job_identifier: ClassVar[str] = "import"

    def __init__(
        self,
        job_service: JobService,
        settings_repo: SettingsRepository,
        game_repo: GameRepository,
        data_dir: Path,
    ) -> None:
        """Initialize the import games job.

        Args:
            job_service: Service for managing job state and events.
            settings_repo: Repository for accessing settings.
            game_repo: Repository for game data.
            data_dir: Base data directory.
        """
        self.job_service = job_service
        self.settings_repo = settings_repo
        self.game_repo = game_repo
        self.data_dir = data_dir

    async def execute(self, job_id: str, **kwargs: Any) -> dict[str, Any]:
        """Execute the import job for a single source.

        Args:
            job_id: The job ID for this import operation.
            **kwargs: Must contain 'source' and 'username'. May contain 'max_games'.

        Returns:
            Dictionary with stored and skipped counts.

        Raises:
            ValueError: If source or username is not provided.
        """
        source = kwargs.get("source")
        username = kwargs.get("username")

        if not source:
            raise ValueError("source is required")
        if not username:
            raise ValueError("username is required")

        max_games = kwargs.get("max_games")
        if max_games is None:
            max_games_str = self.settings_repo.get_setting("sync_max_games")
            max_games = int(max_games_str) if max_games_str else 1000

        from blunder_tutor.fetchers.chesscom import fetch as fetch_chesscom
        from blunder_tutor.fetchers.lichess import fetch as fetch_lichess

        self.job_service.update_job_status(job_id, "running")

        # Initialize progress
        self.job_service.update_job_progress(job_id, 0, max_games)

        # Define progress callback
        def update_progress(current: int, total: int) -> None:
            self.job_service.update_job_progress(job_id, current, total)

        # Fetch games (runs in executor to avoid blocking)
        loop = asyncio.get_event_loop()

        try:
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
            self.job_service.update_job_progress(
                job_id, total_processed, total_processed
            )

            # Refresh game index cache
            await loop.run_in_executor(None, self.game_repo.refresh_index_cache)

            # Complete the job
            result = {"stored": stored, "skipped": skipped}
            self.job_service.complete_job(job_id, result)

            return result

        except Exception as e:
            logger.error(f"Error in import job {job_id}: {e}")
            self.job_service.update_job_status(job_id, "failed", str(e))
            raise
