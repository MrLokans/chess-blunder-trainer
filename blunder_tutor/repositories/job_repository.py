"""Repository for background job tracking."""

from __future__ import annotations

import asyncio
import json
import uuid
from datetime import datetime

from blunder_tutor.events.event_bus import EventBus
from blunder_tutor.events.event_types import JobEvent, StatsEvent
from blunder_tutor.repositories.base import BaseDbRepository


class JobRepository(BaseDbRepository):
    def __init__(self, data_dir, db_path, event_bus: EventBus | None = None):
        super().__init__(data_dir, db_path)
        self.event_bus = event_bus

    def create_job(
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

        with self.connection as conn:
            conn.execute(
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

        # Emit job created event
        if self.event_bus:
            event = JobEvent.create_status_changed(job_id, job_type, "pending")
            asyncio.create_task(self.event_bus.publish(event))

        return job_id

    def update_job_status(
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

        with self.connection as conn:
            if timestamp_field:
                conn.execute(
                    f"""
                    UPDATE background_jobs
                    SET status = ?, error_message = ?, {timestamp_field} = ?
                    WHERE job_id = ?
                    """,
                    (status, error_message, timestamp_value, job_id),
                )
            else:
                conn.execute(
                    """
                    UPDATE background_jobs
                    SET status = ?, error_message = ?
                    WHERE job_id = ?
                    """,
                    (status, error_message, job_id),
                )

        # Emit status change event
        if self.event_bus:
            job = self.get_job(job_id)
            if job:
                event = JobEvent.create_status_changed(
                    job_id=job_id,
                    job_type=job["job_type"],
                    status=status,
                    error_message=error_message,
                )
                asyncio.create_task(self.event_bus.publish(event))

                # Emit stats updated event when job completes
                if status == "completed":
                    stats_event = StatsEvent.create_stats_updated()
                    asyncio.create_task(self.event_bus.publish(stats_event))

    def update_job_progress(
        self,
        job_id: str,
        current: int,
        total: int,
    ) -> None:
        with self.connection as conn:
            conn.execute(
                """
                UPDATE background_jobs
                SET progress_current = ?, progress_total = ?
                WHERE job_id = ?
                """,
                (current, total, job_id),
            )

        # Emit progress update event
        if self.event_bus:
            job = self.get_job(job_id)
            if job:
                event = JobEvent.create_progress_updated(
                    job_id=job_id,
                    job_type=job["job_type"],
                    current=current,
                    total=total,
                )
                asyncio.create_task(self.event_bus.publish(event))

    def complete_job(
        self,
        job_id: str,
        result: dict[str, object],
    ) -> None:
        completed_at = datetime.utcnow().isoformat()
        result_json = json.dumps(result)

        with self.connection as conn:
            conn.execute(
                """
                UPDATE background_jobs
                SET status = 'completed', result_json = ?, completed_at = ?
                WHERE job_id = ?
                """,
                (result_json, completed_at, job_id),
            )

        # Emit completion event
        if self.event_bus:
            job = self.get_job(job_id)
            if job:
                event = JobEvent.create_status_changed(
                    job_id=job_id, job_type=job["job_type"], status="completed"
                )
                asyncio.create_task(self.event_bus.publish(event))

                # Emit stats updated event
                stats_event = StatsEvent.create_stats_updated()
                asyncio.create_task(self.event_bus.publish(stats_event))

    def get_job(self, job_id: str) -> dict[str, object] | None:
        with self.connection as conn:
            row = conn.execute(
                """
                SELECT job_id, job_type, status, username, source,
                       start_date, end_date, max_games, progress_current,
                       progress_total, created_at, started_at, completed_at,
                       error_message, result_json
                FROM background_jobs
                WHERE job_id = ?
                """,
                (job_id,),
            ).fetchone()

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

    def list_jobs(
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

        with self.connection as conn:
            rows = conn.execute(query, params).fetchall()

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

    def get_active_jobs(self) -> list[dict[str, object]]:
        with self.connection as conn:
            rows = conn.execute(
                """
                SELECT job_id, job_type, status, username, source,
                       progress_current, progress_total, created_at, started_at
                FROM background_jobs
                WHERE status IN ('pending', 'running')
                ORDER BY created_at DESC
                """
            ).fetchall()

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

    def delete_job(self, job_id: str) -> bool:
        with self.connection as conn:
            cursor = conn.execute(
                "DELETE FROM background_jobs WHERE job_id = ?",
                (job_id,),
            )
            return cursor.rowcount > 0
