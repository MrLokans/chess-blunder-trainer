from __future__ import annotations

from blunder_tutor.repositories.base import BaseDbRepository


class StatsRepository(BaseDbRepository):
    def get_overview_stats(self) -> dict[str, object]:
        with self.connection as conn:
            # Get game counts
            game_row = conn.execute(
                """
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN analyzed = 1 THEN 1 ELSE 0 END) as analyzed
                FROM game_index_cache
                """
            ).fetchone()

            total_games = game_row[0] if game_row else 0
            # Handle None from SUM when no analyzed games exist
            analyzed_games = (
                int(game_row[1]) if game_row and game_row[1] is not None else 0
            )
            pending_analysis = total_games - analyzed_games

            # Get blunder count
            blunder_row = conn.execute(
                """
                SELECT COUNT(*)
                FROM analysis_moves
                WHERE classification = 3
                """
            ).fetchone()
            total_blunders = blunder_row[0] if blunder_row else 0

        return {
            "total_games": total_games,
            "analyzed_games": analyzed_games,
            "total_blunders": total_blunders,
            "pending_analysis": pending_analysis,
        }

    def get_game_breakdown(
        self,
        source: str | None = None,
        username: str | None = None,
    ) -> list[dict[str, object]]:
        query = """
            SELECT
                source,
                username,
                COUNT(*) as total_games,
                SUM(CASE WHEN analyzed = 1 THEN 1 ELSE 0 END) as analyzed_games,
                COUNT(*) - SUM(CASE WHEN analyzed = 1 THEN 1 ELSE 0 END) as pending_games,
                MIN(end_time_utc) as oldest_game_date,
                MAX(end_time_utc) as newest_game_date
            FROM game_index_cache
            WHERE 1=1
        """
        params: list[str] = []

        if source:
            query += " AND source = ?"
            params.append(source)

        if username:
            query += " AND username = ?"
            params.append(username)

        query += " GROUP BY source, username ORDER BY total_games DESC"

        with self.connection as conn:
            rows = conn.execute(query, params).fetchall()

        return [
            {
                "source": row[0],
                "username": row[1],
                "total_games": row[2],
                "analyzed_games": int(row[3]) if row[3] is not None else 0,
                "pending_games": row[2] - (int(row[3]) if row[3] is not None else 0),
                "oldest_game_date": row[5],
                "newest_game_date": row[6],
            }
            for row in rows
        ]

    def get_blunder_breakdown(
        self,
        username: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> dict[str, object]:
        """Get blunder statistics with date filtering.
        Returns:
            Dictionary with blunder statistics including:
            - total_blunders: Total blunder count
            - avg_cp_loss: Average centipawn loss
            - blunders_by_date: List of date/count pairs
        """
        query = """
            SELECT
                COUNT(*) as total_blunders,
                AVG(am.cp_loss) as avg_cp_loss
            FROM analysis_moves am
            JOIN game_index_cache g ON am.game_id = g.game_id
            WHERE am.classification = 3
        """
        params: list[str] = []

        if username:
            query += " AND g.username = ?"
            params.append(username)

        if start_date:
            query += " AND g.end_time_utc >= ?"
            params.append(start_date)

        if end_date:
            query += " AND g.end_time_utc <= ?"
            params.append(end_date)

        with self.connection as conn:
            row = conn.execute(query, params).fetchone()
            total_blunders = row[0] if row else 0
            avg_cp_loss = row[1] if row else 0.0

            # Get blunders by date
            date_query = """
                SELECT
                    DATE(g.end_time_utc) as date,
                    COUNT(*) as count
                FROM analysis_moves am
                JOIN game_index_cache g ON am.game_id = g.game_id
                WHERE am.classification = 3
            """
            date_params: list[str] = []

            if username:
                date_query += " AND g.username = ?"
                date_params.append(username)

            if start_date:
                date_query += " AND g.end_time_utc >= ?"
                date_params.append(start_date)

            if end_date:
                date_query += " AND g.end_time_utc <= ?"
                date_params.append(end_date)

            date_query += " GROUP BY DATE(g.end_time_utc) ORDER BY date DESC LIMIT 30"

            date_rows = conn.execute(date_query, date_params).fetchall()
            blunders_by_date = [{"date": row[0], "count": row[1]} for row in date_rows]

        return {
            "total_blunders": total_blunders,
            "avg_cp_loss": float(avg_cp_loss) if avg_cp_loss else 0.0,
            "blunders_by_date": blunders_by_date,
        }

    def get_analysis_progress(self) -> dict[str, object]:
        """Get analysis progress metrics from background jobs.

        Returns:
            Dictionary with:
            - total_jobs: Total number of analysis jobs
            - completed_jobs: Completed jobs count
            - failed_jobs: Failed jobs count
            - in_progress_jobs: Jobs currently in progress
        """
        with self.connection as conn:
            row = conn.execute(
                """
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
                    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed,
                    SUM(CASE WHEN status = 'in_progress' THEN 1 ELSE 0 END) as in_progress
                FROM background_jobs
                """
            ).fetchone()

            total_jobs = row[0] if row else 0
            # Handle None from SUM when no jobs exist
            completed_jobs = int(row[1]) if row and row[1] is not None else 0
            failed_jobs = int(row[2]) if row and row[2] is not None else 0
            in_progress_jobs = int(row[3]) if row and row[3] is not None else 0

        return {
            "total_jobs": total_jobs,
            "completed_jobs": completed_jobs,
            "failed_jobs": failed_jobs,
            "in_progress_jobs": in_progress_jobs,
        }

    def get_recent_activity(self, limit: int = 10) -> list[dict[str, object]]:
        with self.connection as conn:
            rows = conn.execute(
                """
                SELECT
                    job_id,
                    job_type,
                    status,
                    username,
                    source,
                    created_at,
                    completed_at
                FROM background_jobs
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

        return [
            {
                "job_id": row[0],
                "job_type": row[1],
                "status": row[2],
                "username": row[3],
                "source": row[4],
                "created_at": row[5],
                "completed_at": row[6],
            }
            for row in rows
        ]
