from __future__ import annotations

import json
import uuid
from datetime import datetime

from blunder_tutor.repositories.base import BaseDbRepository


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
        created_at = datetime.utcnow().isoformat()

        conn = await self.get_connection()
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
                "pending",
                username,
                source,
                start_date,
                end_date,
                max_games,
                created_at,
            ),
        )
        await conn.commit()

        return job_id

    async def update_job_status(
        self,
        job_id: str,
        status: str,
        error_message: str | None = None,
    ) -> None:
        timestamp_field = None
        timestamp_value = datetime.utcnow().isoformat()

        if status == "running":
            timestamp_field = "started_at"
        elif status in ("completed", "failed"):
            timestamp_field = "completed_at"

        conn = await self.get_connection()
        if timestamp_field:
            await conn.execute(
                f"""
                UPDATE background_jobs
                SET status = ?, error_message = ?, {timestamp_field} = ?
                WHERE job_id = ?
                """,
                (status, error_message, timestamp_value, job_id),
            )
        else:
            await conn.execute(
                """
                UPDATE background_jobs
                SET status = ?, error_message = ?
                WHERE job_id = ?
                """,
                (status, error_message, job_id),
            )
        await conn.commit()

    async def update_job_progress(
        self,
        job_id: str,
        current: int,
        total: int,
    ) -> None:
        conn = await self.get_connection()
        await conn.execute(
            """
            UPDATE background_jobs
            SET progress_current = ?, progress_total = ?
            WHERE job_id = ?
            """,
            (current, total, job_id),
        )
        await conn.commit()

    async def complete_job(
        self,
        job_id: str,
        result: dict[str, object],
    ) -> None:
        completed_at = datetime.utcnow().isoformat()
        result_json = json.dumps(result)

        conn = await self.get_connection()
        await conn.execute(
            """
            UPDATE background_jobs
            SET status = 'completed', result_json = ?, completed_at = ?
            WHERE job_id = ?
            """,
            (result_json, completed_at, job_id),
        )
        await conn.commit()

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

        result_json = row[14]
        result = json.loads(result_json) if result_json else None

        return {
            "job_id": row[0],
            "job_type": row[1],
            "status": row[2],
            "username": row[3],
            "source": row[4],
            "start_date": row[5],
            "end_date": row[6],
            "max_games": row[7],
            "progress_current": row[8],
            "progress_total": row[9],
            "created_at": row[10],
            "started_at": row[11],
            "completed_at": row[12],
            "error_message": row[13],
            "result": result,
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

    async def get_active_jobs(self) -> list[dict[str, object]]:
        conn = await self.get_connection()
        async with conn.execute(
            """
            SELECT job_id, job_type, status, username, source,
                   progress_current, progress_total, created_at, started_at
            FROM background_jobs
            WHERE status IN ('pending', 'running')
            ORDER BY created_at DESC
            """
        ) as cursor:
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
            }
            for row in rows
        ]

    async def delete_job(self, job_id: str) -> bool:
        conn = await self.get_connection()
        cursor = await conn.execute(
            "DELETE FROM background_jobs WHERE job_id = ?",
            (job_id,),
        )
        await conn.commit()
        return cursor.rowcount > 0
