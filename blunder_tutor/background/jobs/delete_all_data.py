from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, ClassVar

from blunder_tutor.background.base import BaseJob
from blunder_tutor.background.registry import register_job

if TYPE_CHECKING:
    from blunder_tutor.repositories.data_management import DataManagementRepository
    from blunder_tutor.services.job_service import JobService

logger = logging.getLogger(__name__)

TABLE_ORDER = [
    "puzzle_attempts",
    "analysis_step_status",
    "analysis_moves",
    "analysis_games",
    "background_jobs",
    "game_index_cache",
]


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
        await self.job_service.update_job_status(job_id, "running")
        await self.job_service.update_job_progress(job_id, 0, len(TABLE_ORDER))

        deleted_counts: dict[str, int] = {}

        try:
            conn = await self.data_management_repo.get_connection()

            for i, table in enumerate(TABLE_ORDER):
                cursor = await conn.execute(f"SELECT COUNT(*) FROM {table}")
                count = (await cursor.fetchone())[0]
                deleted_counts[table] = count

                # Don't delete the current job from background_jobs
                if table == "background_jobs":
                    await conn.execute(
                        "DELETE FROM background_jobs WHERE job_id != ?", (job_id,)
                    )
                    deleted_counts[table] = count - 1 if count > 0 else 0
                else:
                    await conn.execute(f"DELETE FROM {table}")

                await conn.commit()
                await self.job_service.update_job_progress(
                    job_id, i + 1, len(TABLE_ORDER)
                )

            total_deleted = sum(deleted_counts.values())
            result = {
                "total_deleted": total_deleted,
                "deleted_by_table": deleted_counts,
            }

            await self.job_service.complete_job(job_id, result)
            return result

        except Exception as e:
            logger.error(f"Error in delete all data job {job_id}: {e}")
            await self.job_service.update_job_status(job_id, "failed", str(e))
            raise
