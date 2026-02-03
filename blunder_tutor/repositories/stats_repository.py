from __future__ import annotations

from blunder_tutor.analysis.tactics import PATTERN_LABELS
from blunder_tutor.constants import COLOR_LABELS, PHASE_LABELS
from blunder_tutor.repositories.base import BaseDbRepository


class StatsRepository(BaseDbRepository):
    async def get_overview_stats(self) -> dict[str, object]:
        conn = await self.get_connection()
        async with conn.execute(
            """
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN analyzed = 1 THEN 1 ELSE 0 END) as analyzed
            FROM game_index_cache
            """
        ) as cursor:
            game_row = await cursor.fetchone()

        total_games = game_row[0] if game_row else 0
        analyzed_games = int(game_row[1]) if game_row and game_row[1] is not None else 0
        pending_analysis = total_games - analyzed_games

        async with conn.execute(
            """
            SELECT COUNT(*)
            FROM analysis_moves
            WHERE classification = 3
            """
        ) as cursor:
            blunder_row = await cursor.fetchone()
        total_blunders = blunder_row[0] if blunder_row else 0

        return {
            "total_games": total_games,
            "analyzed_games": analyzed_games,
            "total_blunders": total_blunders,
            "pending_analysis": pending_analysis,
        }

    async def get_game_breakdown(
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

        conn = await self.get_connection()
        async with conn.execute(query, params) as cursor:
            rows = await cursor.fetchall()

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

    async def get_blunder_breakdown(
        self,
        username: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> dict[str, object]:
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

        conn = await self.get_connection()
        async with conn.execute(query, params) as cursor:
            row = await cursor.fetchone()
        total_blunders = row[0] if row else 0
        avg_cp_loss = row[1] if row else 0.0

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

        async with conn.execute(date_query, date_params) as cursor:
            date_rows = await cursor.fetchall()
        blunders_by_date = [{"date": row[0], "count": row[1]} for row in date_rows]

        return {
            "total_blunders": total_blunders,
            "avg_cp_loss": float(avg_cp_loss) if avg_cp_loss else 0.0,
            "blunders_by_date": blunders_by_date,
        }

    async def get_analysis_progress(self) -> dict[str, object]:
        conn = await self.get_connection()
        async with conn.execute(
            """
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
                SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed,
                SUM(CASE WHEN status = 'in_progress' THEN 1 ELSE 0 END) as in_progress
            FROM background_jobs
            """
        ) as cursor:
            row = await cursor.fetchone()

        total_jobs = row[0] if row else 0
        completed_jobs = int(row[1]) if row and row[1] is not None else 0
        failed_jobs = int(row[2]) if row and row[2] is not None else 0
        in_progress_jobs = int(row[3]) if row and row[3] is not None else 0

        return {
            "total_jobs": total_jobs,
            "completed_jobs": completed_jobs,
            "failed_jobs": failed_jobs,
            "in_progress_jobs": in_progress_jobs,
        }

    async def get_recent_activity(self, limit: int = 10) -> list[dict[str, object]]:
        conn = await self.get_connection()
        async with conn.execute(
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
        ) as cursor:
            rows = await cursor.fetchall()

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

    async def get_blunders_by_phase(
        self,
        username: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> dict[str, object]:
        query = """
            SELECT
                game_phase,
                COUNT(*) as count,
                AVG(cp_loss) as avg_cp_loss
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

        query += " GROUP BY game_phase ORDER BY game_phase"

        conn = await self.get_connection()
        async with conn.execute(query, params) as cursor:
            rows = await cursor.fetchall()

        total = sum(row[1] for row in rows)
        phases = []
        for row in rows:
            phase_int = row[0]
            count = row[1]
            avg_cp_loss = row[2] or 0.0
            phase_label = (
                PHASE_LABELS.get(phase_int, "unknown")
                if phase_int is not None
                else "unknown"
            )
            percentage = (count / total * 100) if total > 0 else 0.0
            phases.append(
                {
                    "phase": phase_label,
                    "phase_id": phase_int,
                    "count": count,
                    "percentage": round(percentage, 1),
                    "avg_cp_loss": round(float(avg_cp_loss), 1),
                }
            )

        return {
            "total_blunders": total,
            "by_phase": phases,
        }

    async def get_blunders_by_eco(
        self,
        username: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        limit: int = 10,
    ) -> dict[str, object]:
        query = """
            SELECT
                ag.eco_code,
                ag.eco_name,
                COUNT(*) as blunder_count,
                AVG(am.cp_loss) as avg_cp_loss,
                COUNT(DISTINCT ag.game_id) as game_count
            FROM analysis_moves am
            JOIN analysis_games ag ON am.game_id = ag.game_id
            JOIN game_index_cache g ON am.game_id = g.game_id
            WHERE am.classification = 3 AND ag.eco_code IS NOT NULL
        """
        params: list[object] = []

        if username:
            query += " AND g.username = ?"
            params.append(username)

        if start_date:
            query += " AND g.end_time_utc >= ?"
            params.append(start_date)

        if end_date:
            query += " AND g.end_time_utc <= ?"
            params.append(end_date)

        query += (
            " GROUP BY ag.eco_code, ag.eco_name ORDER BY blunder_count DESC LIMIT ?"
        )
        params.append(limit)

        conn = await self.get_connection()
        async with conn.execute(query, params) as cursor:
            rows = await cursor.fetchall()

        total = sum(row[2] for row in rows)
        openings = []
        for row in rows:
            eco_code = row[0]
            eco_name = row[1]
            blunder_count = row[2]
            avg_cp_loss = row[3] or 0.0
            game_count = row[4]
            percentage = (blunder_count / total * 100) if total > 0 else 0.0
            openings.append(
                {
                    "eco_code": eco_code,
                    "eco_name": eco_name,
                    "count": blunder_count,
                    "percentage": round(percentage, 1),
                    "avg_cp_loss": round(float(avg_cp_loss), 1),
                    "game_count": game_count,
                }
            )

        return {
            "total_blunders": total,
            "by_opening": openings,
        }

    async def get_blunders_by_color(
        self,
        username: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> dict[str, object]:
        if not username:
            return {"total_blunders": 0, "by_color": [], "blunders_by_date": []}

        username_lower = username.lower()

        query = """
            SELECT
                CASE
                    WHEN LOWER(g.white) = ? THEN 0
                    WHEN LOWER(g.black) = ? THEN 1
                END as user_color,
                COUNT(*) as count,
                AVG(am.cp_loss) as avg_cp_loss
            FROM analysis_moves am
            JOIN game_index_cache g ON am.game_id = g.game_id
            WHERE am.classification = 3
              AND g.username = ?
              AND am.player = CASE
                    WHEN LOWER(g.white) = ? THEN 0
                    WHEN LOWER(g.black) = ? THEN 1
                END
        """
        params: list[object] = [
            username_lower,
            username_lower,
            username,
            username_lower,
            username_lower,
        ]

        if start_date:
            query += " AND g.end_time_utc >= ?"
            params.append(start_date)

        if end_date:
            query += " AND g.end_time_utc <= ?"
            params.append(end_date)

        query += " GROUP BY user_color ORDER BY user_color"

        conn = await self.get_connection()
        async with conn.execute(query, params) as cursor:
            rows = await cursor.fetchall()

        total = sum(row[1] for row in rows)
        colors = []
        for row in rows:
            color_int = row[0]
            count = row[1]
            avg_cp_loss = row[2] or 0.0
            color_label = (
                COLOR_LABELS.get(color_int, "unknown")
                if color_int is not None
                else "unknown"
            )
            percentage = (count / total * 100) if total > 0 else 0.0
            colors.append(
                {
                    "color": color_label,
                    "color_id": color_int,
                    "count": count,
                    "percentage": round(percentage, 1),
                    "avg_cp_loss": round(float(avg_cp_loss), 1),
                }
            )

        date_query = """
            SELECT
                DATE(g.end_time_utc) as date,
                CASE
                    WHEN LOWER(g.white) = ? THEN 0
                    WHEN LOWER(g.black) = ? THEN 1
                END as user_color,
                COUNT(*) as count
            FROM analysis_moves am
            JOIN game_index_cache g ON am.game_id = g.game_id
            WHERE am.classification = 3
              AND g.username = ?
              AND am.player = CASE
                    WHEN LOWER(g.white) = ? THEN 0
                    WHEN LOWER(g.black) = ? THEN 1
                END
        """
        date_params: list[object] = [
            username_lower,
            username_lower,
            username,
            username_lower,
            username_lower,
        ]

        if start_date:
            date_query += " AND g.end_time_utc >= ?"
            date_params.append(start_date)

        if end_date:
            date_query += " AND g.end_time_utc <= ?"
            date_params.append(end_date)

        date_query += " GROUP BY date, user_color ORDER BY date DESC LIMIT 60"

        async with conn.execute(date_query, date_params) as cursor:
            date_rows = await cursor.fetchall()

        blunders_by_date = [
            {
                "date": row[0],
                "color": COLOR_LABELS.get(row[1], "unknown"),
                "count": row[2],
            }
            for row in date_rows
        ]

        return {
            "total_blunders": total,
            "by_color": colors,
            "blunders_by_date": blunders_by_date,
        }

    async def get_games_by_date(
        self,
        username: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> list[dict[str, object]]:
        query = """
            SELECT
                DATE(g.end_time_utc) as game_date,
                COUNT(DISTINCT g.game_id) as game_count,
                AVG(game_stats.avg_cpl) as avg_cpl,
                SUM(game_stats.blunder_count) as total_blunders
            FROM game_index_cache g
            LEFT JOIN (
                SELECT
                    game_id,
                    AVG(cp_loss) as avg_cpl,
                    SUM(CASE WHEN classification = 3 THEN 1 ELSE 0 END) as blunder_count
                FROM analysis_moves
                GROUP BY game_id
            ) game_stats ON g.game_id = game_stats.game_id
            WHERE g.analyzed = 1
        """
        params: list[object] = []

        if username:
            query += " AND g.username = ?"
            params.append(username)

        if start_date:
            query += " AND g.end_time_utc >= ?"
            params.append(start_date)

        if end_date:
            query += " AND g.end_time_utc <= ?"
            params.append(end_date)

        query += " GROUP BY game_date ORDER BY game_date ASC"

        conn = await self.get_connection()
        async with conn.execute(query, params) as cursor:
            rows = await cursor.fetchall()

        return [
            {
                "date": row[0],
                "game_count": row[1],
                "avg_cpl": round(float(row[2]), 1) if row[2] else 0.0,
                "blunders": int(row[3]) if row[3] else 0,
            }
            for row in rows
        ]

    async def get_games_by_hour(
        self,
        username: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> list[dict[str, object]]:
        query = """
            SELECT
                CAST(strftime('%H', g.end_time_utc) AS INTEGER) as hour,
                COUNT(DISTINCT g.game_id) as game_count,
                AVG(game_stats.avg_cpl) as avg_cpl,
                SUM(game_stats.blunder_count) as total_blunders
            FROM game_index_cache g
            LEFT JOIN (
                SELECT
                    game_id,
                    AVG(cp_loss) as avg_cpl,
                    SUM(CASE WHEN classification = 3 THEN 1 ELSE 0 END) as blunder_count
                FROM analysis_moves
                GROUP BY game_id
            ) game_stats ON g.game_id = game_stats.game_id
            WHERE g.analyzed = 1
        """
        params: list[object] = []

        if username:
            query += " AND g.username = ?"
            params.append(username)

        if start_date:
            query += " AND g.end_time_utc >= ?"
            params.append(start_date)

        if end_date:
            query += " AND g.end_time_utc <= ?"
            params.append(end_date)

        query += " GROUP BY hour ORDER BY hour ASC"

        conn = await self.get_connection()
        async with conn.execute(query, params) as cursor:
            rows = await cursor.fetchall()

        return [
            {
                "hour": row[0],
                "game_count": row[1],
                "avg_cpl": round(float(row[2]), 1) if row[2] else 0.0,
                "blunders": int(row[3]) if row[3] else 0,
            }
            for row in rows
        ]

    async def get_blunders_by_tactical_pattern(
        self,
        username: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> dict[str, object]:
        """Get blunder statistics grouped by tactical pattern."""
        query = """
            SELECT
                tactical_pattern,
                COUNT(*) as count,
                AVG(cp_loss) as avg_cp_loss
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

        query += " GROUP BY tactical_pattern ORDER BY count DESC"

        conn = await self.get_connection()
        async with conn.execute(query, params) as cursor:
            rows = await cursor.fetchall()

        total = sum(row[1] for row in rows)
        patterns = []
        for row in rows:
            pattern_int = row[0]
            count = row[1]
            avg_cp_loss = row[2] or 0.0
            pattern_label = (
                PATTERN_LABELS.get(pattern_int, "Unknown")
                if pattern_int is not None
                else "Not Classified"
            )
            percentage = (count / total * 100) if total > 0 else 0.0
            patterns.append(
                {
                    "pattern": pattern_label,
                    "pattern_id": pattern_int,
                    "count": count,
                    "percentage": round(percentage, 1),
                    "avg_cp_loss": round(float(avg_cp_loss), 1),
                }
            )

        return {
            "total_blunders": total,
            "by_pattern": patterns,
        }
