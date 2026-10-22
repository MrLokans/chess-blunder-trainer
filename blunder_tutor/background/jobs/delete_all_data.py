from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar

from blunder_tutor.background.base import BaseJob
from blunder_tutor.background.registry import register_job

if TYPE_CHECKING:
    from blunder_tutor.repositories.data_management import DataManagementRepository
    from blunder_tutor.services.job_service import JobService, ProgressCallback


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
            1,
            lambda progress: self._delete_all(job_id, progress),
        )

    async def _delete_all(
        self,
        job_id: str,
        progress: ProgressCallback,
    ) -> dict[str, Any]:
        deleted_counts = await self.data_management_repo.delete_all_data(
            keep_job_id=job_id
        )
        await progress(1)
        return {
            "total_deleted": sum(deleted_counts.values()),
            "deleted_by_table": deleted_counts,
        }
