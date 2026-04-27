from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, ClassVar

from blunder_tutor.background.base import BaseJob
from blunder_tutor.background.registry import register_job

if TYPE_CHECKING:
    from blunder_tutor.repositories.data_management import DataManagementRepository
    from blunder_tutor.services.job_service import JobService, ProgressCallback

logger = logging.getLogger(__name__)

TABLE_ORDER = (
    "puzzle_attempts",
    "analysis_step_status",
    "analysis_moves",
    "analysis_games",
    "background_jobs",
    "game_index_cache",
)


@register_job
class DeleteAllDataJob(BaseJob):
    job_identifier: ClassVar[str] = "delete_all_data"

    def __init__(
        self,
        job_service: JobService,
        data_management_repo: DataManagementRepository,
    ) -> None:
        self.job_service = job_service
        self.data_management_repo = data_management_repo

    async def execute(self, job_id: str, **kwargs: Any) -> dict[str, Any]:
        return await self.job_service.run_with_lifecycle(
            job_id,
            len(TABLE_ORDER),
            lambda progress: self._delete_all(job_id, progress),
        )

    async def _delete_all(
        self,
        job_id: str,
        progress: ProgressCallback,
    ) -> dict[str, Any]:
        deleted_counts: dict[str, int] = {}
        conn = await self.data_management_repo.get_connection()

        for i, table in enumerate(TABLE_ORDER):
            deleted_counts[table] = await _truncate_table(conn, table, job_id)
            await progress(i + 1)

        return {
            "total_deleted": sum(deleted_counts.values()),
            "deleted_by_table": deleted_counts,
        }


async def _truncate_table(conn: Any, table: str, job_id: str) -> int:
    cursor = await conn.execute(f"SELECT COUNT(*) FROM {table}")
    count = (await cursor.fetchone())[0]
    if table == "background_jobs":
        # Don't delete the current job from background_jobs
        await conn.execute(
            "DELETE FROM background_jobs WHERE job_id != ?",
            (job_id,),
        )
        deleted = count - 1 if count > 0 else 0
    else:
        await conn.execute(f"DELETE FROM {table}")
        deleted = count
    await conn.commit()
    return deleted
