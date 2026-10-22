from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

from blunder_tutor.background.jobs.delete_all_data import DeleteAllDataJob
from blunder_tutor.constants import JOB_TYPE_DELETE_ALL_DATA, JOB_TYPE_SYNC
from blunder_tutor.repositories.data_management import (
    _WIPE_TABLES,
    DataManagementRepository,
)
from blunder_tutor.repositories.job_repository import JobRepository

# Settings and profiles survive a data wipe by design.
_KEPT_TABLES = {
    "alembic_version",
    "app_settings",
    "profile",
    "profile_preferences",
    "profile_stats",
}


def test_wipe_covers_every_user_table(db_path: Path):
    with closing(sqlite3.connect(db_path)) as conn:
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' "
                "AND name NOT LIKE 'sqlite_%'"
            )
        }
    assert {table for table, _ in _WIPE_TABLES} == tables - _KEPT_TABLES


async def test_job_wipes_in_one_call_and_keeps_own_row(
    db_path: Path, job_repo: JobRepository
):
    other = await job_repo.create_job(JOB_TYPE_SYNC)
    own = await job_repo.create_job(JOB_TYPE_DELETE_ALL_DATA)
    job_service = MagicMock()

    async def run_with_lifecycle(_job_id, _total, body):
        return await body(AsyncMock())

    job_service.run_with_lifecycle = run_with_lifecycle

    async with DataManagementRepository(db_path) as repo:
        result = await DeleteAllDataJob(job_service, repo).execute(own)

    assert result["deleted_by_table"]["background_jobs"] == 1
    assert await job_repo.get_job(other) is None
    assert await job_repo.get_job(own) is not None
