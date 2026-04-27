from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, ClassVar

from blunder_tutor.background.base import BaseJob
from blunder_tutor.background.registry import register_job
from blunder_tutor.services.trap_backfill_service import TrapBackfillService

if TYPE_CHECKING:
    from blunder_tutor.repositories.game_repository import GameRepository
    from blunder_tutor.repositories.trap_repository import TrapRepository
    from blunder_tutor.services.job_service import JobService, ProgressCallback

logger = logging.getLogger(__name__)


@register_job
class BackfillTrapsJob(BaseJob):
    job_identifier: ClassVar[str] = "backfill_traps"

    def __init__(
        self,
        job_service: JobService,
        game_repo: GameRepository,
        trap_repo: TrapRepository,
    ) -> None:
        self.job_service = job_service
        self._service = TrapBackfillService(
            game_repo=game_repo,
            trap_repo=trap_repo,
        )

    async def execute(self, job_id: str, **kwargs: Any) -> dict[str, Any]:
        game_ids = await self._service.get_games_needing_backfill()

        if not game_ids:
            empty = {"games_processed": 0, "games_with_traps": 0}
            await self.job_service.complete_job(job_id, empty)
            return empty

        return await self.job_service.run_with_lifecycle(
            job_id,
            len(game_ids),
            lambda progress: self._backfill(job_id, game_ids, progress),
        )

    async def _backfill(
        self,
        job_id: str,
        game_ids: list[str],
        progress: ProgressCallback,
    ) -> dict[str, Any]:
        games_processed = 0
        games_with_traps = 0
        for i, game_id in enumerate(game_ids):
            if await self._is_cancelled(job_id):
                break
            count = await self._service.backfill_game(game_id)
            games_processed += 1
            if count > 0:
                games_with_traps += 1
            await progress(i + 1)
        return {
            "games_processed": games_processed,
            "games_with_traps": games_with_traps,
        }

    async def _is_cancelled(self, job_id: str) -> bool:
        job = await self.job_service.get_job(job_id)
        return bool(job and job.get("status") == "failed")
