from __future__ import annotations

import json
import uuid

from blunder_tutor.constants import (
    JOB_STATUS_COMPLETED,
    JOB_STATUS_FAILED,
    JOB_STATUS_PENDING,
    JOB_STATUS_RUNNING,
    JOB_TYPE_IMPORT,
    JOB_TYPE_SYNC,
)
from blunder_tutor.repositories.base import BaseDbRepository
from blunder_tutor.utils.time import now_iso

_ACTIVE_STATUSES = (JOB_STATUS_PENDING, JOB_STATUS_RUNNING)


class JobRepository(BaseDbRepository):
    async def create_job(
        self,
        job_type: str,
        username: str | None = None,
        source: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        max_games: int | None = None,
    ) -> str:
        job_id = str(uuid.uuid4())
        created_at = now_iso()

        async with self.write_transaction() as conn:
            await conn.execute(
                """
                INSERT INTO background_jobs (
                    job_id, job_type, status, username, source,
                    start_date, end_date, max_games, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    job_id,
                    job_type,
                    JOB_STATUS_PENDING,
                    username,
                    source,
                    start_date,
                    end_date,
                    max_games,
                    created_at,
                ),
            )

        return job_id

    async def update_job_status(
        self,
        job_id: str,
        status: str,
        error_message: str | None = None,
    ) -> bool:
        """False when the job already reached a terminal state (e.g. stopped by the
        user), which is never overwritten."""
        timestamp_field = None
        timestamp_value = now_iso()

        if status == JOB_STATUS_RUNNING:
            timestamp_field = "started_at"
        elif status in (JOB_STATUS_COMPLETED, JOB_STATUS_FAILED):
            timestamp_field = "completed_at"

        async with self.write_transaction() as conn:
            if timestamp_field:
                cursor = await conn.execute(
                    f"""
                    UPDATE background_jobs
                    SET status = ?, error_message = ?, {timestamp_field} = ?
                    WHERE job_id = ? AND status IN (?, ?)
                    """,
                    (
                        status,
                        error_message,
                        timestamp_value,
                        job_id,
                        *_ACTIVE_STATUSES,
                    ),
                )
            else:
                cursor = await conn.execute(
                    """
                    UPDATE background_jobs
                    SET status = ?, error_message = ?
                    WHERE job_id = ? AND status IN (?, ?)
                    """,
                    (status, error_message, job_id, *_ACTIVE_STATUSES),
                )
            return cursor.rowcount > 0

    async def update_job_progress(
        self,
        job_id: str,
        current: int,
        total: int,
    ) -> None:
        async with self.write_transaction() as conn:
            await conn.execute(
                """
                UPDATE background_jobs
                SET progress_current = ?, progress_total = ?
                WHERE job_id = ?
                """,
                (current, total, job_id),
            )

    async def complete_job(
        self,
        job_id: str,
        result: dict[str, object],
    ) -> bool:
        completed_at = now_iso()
        result_json = json.dumps(result)

        async with self.write_transaction() as conn:
            cursor = await conn.execute(
                """
                UPDATE background_jobs
                SET status = ?, result_json = ?, completed_at = ?
                WHERE job_id = ? AND status IN (?, ?)
                """,
                (
                    JOB_STATUS_COMPLETED,
                    result_json,
                    completed_at,
                    job_id,
                    *_ACTIVE_STATUSES,
                ),
            )
            return cursor.rowcount > 0

    async def get_job(self, job_id: str) -> dict[str, object] | None:
        conn = await self.get_connection()
        async with conn.execute(
            """
            SELECT job_id, job_type, status, username, source,
                   start_date, end_date, max_games, progress_current,
                   progress_total, created_at, started_at, completed_at,
                   error_message, result_json
            FROM background_jobs
            WHERE job_id = ?
            """,
            (job_id,),
        ) as cursor:
            row = await cursor.fetchone()

        if not row:
            return None

        result_json = row["result_json"]
        return {
            **{key: row[key] for key in row.keys() if key != "result_json"},  # noqa: SIM118 — aiosqlite.Row iterates values; .keys() is required.
            "result": json.loads(result_json) if result_json else None,
        }

    async def list_jobs(
        self,
        job_type: str | None = None,
        status: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, object]]:
        query = """
            SELECT job_id, job_type, status, username, source,
                   progress_current, progress_total, created_at,
                   started_at, completed_at, error_message
            FROM background_jobs
            WHERE 1=1
        """
        params: list[object] = []

        if job_type:
            query += " AND job_type = ?"
            params.append(job_type)

        if status:
            query += " AND status = ?"
            params.append(status)

        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        conn = await self.get_connection()
        async with conn.execute(query, params) as cursor:
            rows = await cursor.fetchall()

        return [
            {
                "job_id": row[0],
                "job_type": row[1],
                "status": row[2],
                "username": row[3],
                "source": row[4],
                "progress_current": row[5],
                "progress_total": row[6],
                "created_at": row[7],
                "started_at": row[8],
                "completed_at": row[9],
                "error_message": row[10],
            }
            for row in rows
        ]

    async def fail_interrupted_jobs(self) -> int:
        """Only safe at startup: the job queue is in-memory, so any active row is orphaned."""
        async with self.write_transaction() as conn:
            cursor = await conn.execute(
                """
                UPDATE background_jobs
                SET status = ?, error_message = 'interrupted', completed_at = ?
                WHERE status IN (?, ?)
                """,
                (JOB_STATUS_FAILED, now_iso(), *_ACTIVE_STATUSES),
            )
            return cursor.rowcount

    async def delete_job(self, job_id: str) -> bool:
        async with self.write_transaction() as conn:
            cursor = await conn.execute(
                "DELETE FROM background_jobs WHERE job_id = ?",
                (job_id,),
            )
            return cursor.rowcount > 0

    async def get_sync_attempt_state(
        self, source: str, username: str
    ) -> tuple[str | None, bool]:
        """(latest attempt of any outcome, whether one is still pending/running), so the
        scheduler neither overlaps a running sync nor retries a failing one every tick."""
        conn = await self.get_connection()
        async with conn.execute(
            """
            SELECT MAX(created_at), COALESCE(MAX(status IN (?, ?)), 0)
            FROM background_jobs
            WHERE source = ?
              AND LOWER(username) = LOWER(?)
              AND job_type IN (?, ?)
            """,
            (*_ACTIVE_STATUSES, source, username, JOB_TYPE_IMPORT, JOB_TYPE_SYNC),
        ) as cursor:
            row = await cursor.fetchone()
        return row[0], bool(row[1])

    async def get_last_completed_sync_at(
        self, source: str, username: str
    ) -> str | None:
        """Case-insensitive: historical jobs may carry mixed-case usernames."""
        conn = await self.get_connection()
        async with conn.execute(
            """
            SELECT MAX(completed_at) FROM background_jobs
            WHERE source = ?
              AND LOWER(username) = LOWER(?)
              AND status = ?
              AND job_type IN (?, ?)
            """,
            (source, username, JOB_STATUS_COMPLETED, JOB_TYPE_IMPORT, JOB_TYPE_SYNC),
        ) as cursor:
            row = await cursor.fetchone()
        if row is None or row[0] is None:
            return None
        return row[0]
