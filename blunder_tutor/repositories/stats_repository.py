from __future__ import annotations

import dataclasses
import statistics
from collections import defaultdict

from blunder_tutor.analysis.tactics import PATTERN_LABELS
from blunder_tutor.constants import COLOR_LABELS, PHASE_LABELS
from blunder_tutor.repositories.base import BaseDbRepository
from blunder_tutor.utils.accuracy import game_accuracy
from blunder_tutor.utils.time_control import (
    GAME_TYPE_LABELS,
)

CATASTROPHIC_CP_LOSS = 500
WINNING_THRESHOLD_CP = 200
LOSING_THRESHOLD_CP = -200

COLLAPSE_BUCKET_SIZE = 5
COLLAPSE_MAX_BUCKET_START = 41


@dataclasses.dataclass(frozen=True)
class StatsFilter:
    start_date: str | None = None
    end_date: str | None = None
    game_types: list[int] | None = None
    game_phases: list[int] | None = None

    def append_to(
        self,
        clause: str,
        params: list[object],
        *,
        table_alias: str = "g",
        moves_alias: str = "am",
        include_phase: bool = True,
    ) -> str:
        if self.start_date:
            clause += f" AND {table_alias}.end_time_utc >= ?"
            params.append(self.start_date)
        if self.end_date:
            clause += f" AND {table_alias}.end_time_utc <= ?"
            params.append(self.end_date + " 23:59:59")
        if self.game_types:
            placeholders = ",".join("?" for _ in self.game_types)
            clause += f" AND {table_alias}.game_type IN ({placeholders})"
            params.extend(self.game_types)
        if include_phase and self.game_phases:
            placeholders = ",".join("?" for _ in self.game_phases)
            clause += f" AND {moves_alias}.game_phase IN ({placeholders})"
            params.extend(self.game_phases)
        return clause


PLAYER_SIDE_FILTER = """
    AND am.player = CASE
        WHEN LOWER(g.white) = LOWER(g.username) THEN 0
        WHEN LOWER(g.black) = LOWER(g.username) THEN 1
    END
"""


class StatsRepository(BaseDbRepository):
    async def get_overview_stats(
        self,
        filters: StatsFilter | None = None,
    ) -> dict[str, object]:
        filters = filters or StatsFilter()
        conn = await self.get_connection()

        game_where = "WHERE 1=1"
        game_params: list[object] = []
        game_where = filters.append_to(game_where, game_params, include_phase=False)

        async with conn.execute(
            f"""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN analyzed = 1 THEN 1 ELSE 0 END) as analyzed
            FROM game_index_cache g
            {game_where}
            """,
            game_params,
        ) as cursor:
            game_row = await cursor.fetchone()

        total_games = game_row[0] if game_row else 0
        analyzed_games = int(game_row[1]) if game_row and game_row[1] is not None else 0
        pending_analysis = total_games - analyzed_games

        blunder_where = f"""
            WHERE am.classification = 3
            {PLAYER_SIDE_FILTER}
        """
        blunder_params: list[object] = []
        blunder_where = filters.append_to(blunder_where, blunder_params)

        async with conn.execute(
            f"""
            SELECT COUNT(*)
            FROM analysis_moves am
            JOIN game_index_cache g ON am.game_id = g.game_id
            {blunder_where}
            """,
            blunder_params,
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
        filters: StatsFilter | None = None,
    ) -> dict[str, object]:
        filters = filters or StatsFilter()
        query = f"""
            SELECT
                COUNT(*) as total_blunders,
                AVG(am.cp_loss) as avg_cp_loss
            FROM analysis_moves am
            JOIN game_index_cache g ON am.game_id = g.game_id
            WHERE am.classification = 3
            {PLAYER_SIDE_FILTER}
        """
        params: list[object] = []
        query = filters.append_to(query, params)

        conn = await self.get_connection()
        async with conn.execute(query, params) as cursor:
            row = await cursor.fetchone()
        total_blunders = row[0] if row else 0
        avg_cp_loss = row[1] if row else 0.0

        date_query = f"""
            SELECT
                DATE(g.end_time_utc) as date,
                COUNT(*) as count
            FROM analysis_moves am
            JOIN game_index_cache g ON am.game_id = g.game_id
            WHERE am.classification = 3
            AND g.end_time_utc IS NOT NULL
            {PLAYER_SIDE_FILTER}
        """
        date_params: list[object] = []
        date_query = filters.append_to(date_query, date_params)
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
        filters: StatsFilter | None = None,
    ) -> dict[str, object]:
        filters = filters or StatsFilter()
        query = f"""
            SELECT
                game_phase,
                COUNT(*) as count,
                AVG(cp_loss) as avg_cp_loss
            FROM analysis_moves am
            JOIN game_index_cache g ON am.game_id = g.game_id
            WHERE am.classification = 3
            {PLAYER_SIDE_FILTER}
        """
        params: list[object] = []
        query = filters.append_to(query, params)
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
        filters: StatsFilter | None = None,
        limit: int = 10,
    ) -> dict[str, object]:
        filters = filters or StatsFilter()
        query = f"""
            SELECT
                ag.eco_code,
                ag.eco_name,
                am.cp_loss,
                ag.game_id
            FROM analysis_moves am
            JOIN analysis_games ag ON am.game_id = ag.game_id
            JOIN game_index_cache g ON am.game_id = g.game_id
            WHERE am.classification = 3 AND ag.eco_code IS NOT NULL
            {PLAYER_SIDE_FILTER}
        """
        params: list[object] = []
        query = filters.append_to(query, params)

        conn = await self.get_connection()
        async with conn.execute(query, params) as cursor:
            rows = await cursor.fetchall()

        eco_stats: dict[tuple[str, str], dict[str, object]] = {}

        for row in rows:
            eco_code = row[0]
            eco_name = row[1]
            cp_loss = row[2] or 0
            game_id = row[3]

            key = (eco_code, eco_name)
            if key not in eco_stats:
                eco_stats[key] = {
                    "count": 0,
                    "total_cp_loss": 0.0,
                    "game_ids": set(),
                }

            eco_stats[key]["count"] += 1
            eco_stats[key]["total_cp_loss"] += cp_loss
            eco_stats[key]["game_ids"].add(game_id)

        sorted_ecos = sorted(
            eco_stats.items(), key=lambda x: x[1]["count"], reverse=True
        )[:limit]

        total = sum(stats["count"] for _, stats in sorted_ecos)
        openings = []
        for (eco_code, eco_name), stats in sorted_ecos:
            count = stats["count"]
            avg_cp_loss = stats["total_cp_loss"] / count if count > 0 else 0.0
            game_count = len(stats["game_ids"])
            percentage = (count / total * 100) if total > 0 else 0.0
            openings.append(
                {
                    "eco_code": eco_code,
                    "eco_name": eco_name,
                    "count": count,
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
        filters: StatsFilter | None = None,
    ) -> dict[str, object]:
        filters = filters or StatsFilter()
        query = f"""
            SELECT
                CASE
                    WHEN LOWER(g.white) = LOWER(g.username) THEN 0
                    WHEN LOWER(g.black) = LOWER(g.username) THEN 1
                END as user_color,
                COUNT(*) as count,
                AVG(am.cp_loss) as avg_cp_loss
            FROM analysis_moves am
            JOIN game_index_cache g ON am.game_id = g.game_id
            WHERE am.classification = 3
            {PLAYER_SIDE_FILTER}
        """
        params: list[object] = []
        query = filters.append_to(query, params)
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

        date_query = f"""
            SELECT
                DATE(g.end_time_utc) as date,
                CASE
                    WHEN LOWER(g.white) = LOWER(g.username) THEN 0
                    WHEN LOWER(g.black) = LOWER(g.username) THEN 1
                END as user_color,
                COUNT(*) as count
            FROM analysis_moves am
            JOIN game_index_cache g ON am.game_id = g.game_id
            WHERE am.classification = 3
              AND g.end_time_utc IS NOT NULL
            {PLAYER_SIDE_FILTER}
        """
        date_params: list[object] = []
        date_query = filters.append_to(date_query, date_params)
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
        filters: StatsFilter | None = None,
    ) -> list[dict[str, object]]:
        filters = filters or StatsFilter()
        query = f"""
            SELECT
                g.game_id,
                DATE(g.end_time_utc) as game_date,
                am.cp_loss
            FROM analysis_moves am
            JOIN game_index_cache g ON am.game_id = g.game_id
            WHERE g.analyzed = 1
            {PLAYER_SIDE_FILTER}
        """
        params: list[object] = []
        query = filters.append_to(query, params)
        query += " ORDER BY game_date ASC"

        conn = await self.get_connection()
        async with conn.execute(query, params) as cursor:
            rows = await cursor.fetchall()

        game_date_losses: dict[tuple[str, str], list[int]] = defaultdict(list)
        for game_id, game_date, cp_loss in rows:
            game_date_losses[(game_id, game_date)].append(cp_loss)

        date_accuracies: dict[str, list[float]] = defaultdict(list)
        for (_, game_date), losses in game_date_losses.items():
            date_accuracies[game_date].append(game_accuracy(losses))

        return [
            {
                "date": d,
                "game_count": len(accs),
                "avg_accuracy": round(sum(accs) / len(accs), 1),
            }
            for d, accs in sorted(date_accuracies.items())
        ]

    async def get_games_by_hour(
        self,
        filters: StatsFilter | None = None,
    ) -> list[dict[str, object]]:
        filters = filters or StatsFilter()
        query = f"""
            SELECT
                g.game_id,
                CAST(strftime('%H', g.end_time_utc) AS INTEGER) as hour,
                am.cp_loss
            FROM analysis_moves am
            JOIN game_index_cache g ON am.game_id = g.game_id
            WHERE g.analyzed = 1
            {PLAYER_SIDE_FILTER}
        """
        params: list[object] = []
        query = filters.append_to(query, params)

        conn = await self.get_connection()
        async with conn.execute(query, params) as cursor:
            rows = await cursor.fetchall()

        game_hour_losses: dict[tuple[str, int], list[int]] = defaultdict(list)
        for game_id, hour, cp_loss in rows:
            game_hour_losses[(game_id, hour)].append(cp_loss)

        hour_accuracies: dict[int, list[float]] = defaultdict(list)
        for (_, hour), losses in game_hour_losses.items():
            hour_accuracies[hour].append(game_accuracy(losses))

        return [
            {
                "hour": h,
                "game_count": len(accs),
                "avg_accuracy": round(sum(accs) / len(accs), 1),
            }
            for h, accs in sorted(hour_accuracies.items())
        ]

    async def get_blunders_by_tactical_pattern(
        self,
        filters: StatsFilter | None = None,
    ) -> dict[str, object]:
        filters = filters or StatsFilter()
        query = f"""
            SELECT
                tactical_pattern,
                COUNT(*) as count,
                AVG(cp_loss) as avg_cp_loss
            FROM analysis_moves am
            JOIN game_index_cache g ON am.game_id = g.game_id
            WHERE am.classification = 3
            {PLAYER_SIDE_FILTER}
        """
        params: list[object] = []
        query = filters.append_to(query, params)
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

    async def get_blunders_by_game_type(
        self,
        filters: StatsFilter | None = None,
    ) -> dict[str, object]:
        filters = filters or StatsFilter()
        query = f"""
            SELECT
                g.game_type,
                COUNT(*) as count,
                AVG(am.cp_loss) as avg_cp_loss
            FROM analysis_moves am
            JOIN game_index_cache g ON am.game_id = g.game_id
            WHERE am.classification = 3
            {PLAYER_SIDE_FILTER}
        """
        params: list[object] = []
        query = filters.append_to(query, params)
        query += " GROUP BY g.game_type ORDER BY g.game_type"

        conn = await self.get_connection()
        async with conn.execute(query, params) as cursor:
            rows = await cursor.fetchall()

        total = sum(row[1] for row in rows)
        game_types = []
        for row in rows:
            game_type_int = row[0]
            count = row[1]
            avg_cp_loss = row[2] or 0.0
            game_type_label = GAME_TYPE_LABELS.get(game_type_int, "unknown")
            percentage = (count / total * 100) if total > 0 else 0.0
            game_types.append(
                {
                    "game_type": game_type_label,
                    "game_type_id": game_type_int if game_type_int is not None else -1,
                    "count": count,
                    "percentage": round(percentage, 1),
                    "avg_cp_loss": round(float(avg_cp_loss), 1),
                }
            )

        return {
            "total_blunders": int(total),
            "by_game_type": game_types,
        }

    async def get_blunders_by_phase_filtered(
        self,
        filters: StatsFilter | None = None,
        player_colors: list[int] | None = None,
    ) -> dict[str, object]:
        filters = filters or StatsFilter()
        query = f"""
            SELECT
                am.game_phase,
                COUNT(*) as count,
                AVG(am.cp_loss) as avg_cp_loss
            FROM analysis_moves am
            JOIN game_index_cache g ON am.game_id = g.game_id
            WHERE am.classification = 3
            {PLAYER_SIDE_FILTER}
        """
        params: list[object] = []
        query = filters.append_to(query, params)

        if player_colors:
            placeholders = ",".join("?" * len(player_colors))
            query += f" AND am.player IN ({placeholders})"
            params.extend(player_colors)

        query += " GROUP BY am.game_phase ORDER BY am.game_phase"

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
                    "avg_cp_loss": round(avg_cp_loss, 1),
                }
            )

        return {
            "total_blunders": total,
            "by_phase": phases,
        }

    async def get_blunders_by_difficulty(
        self,
        filters: StatsFilter | None = None,
    ) -> dict[str, object]:
        filters = filters or StatsFilter()
        query = f"""
            SELECT
                CASE
                    WHEN am.difficulty IS NULL THEN 'unscored'
                    WHEN am.difficulty <= 30 THEN 'easy'
                    WHEN am.difficulty <= 60 THEN 'medium'
                    ELSE 'hard'
                END as diff_bucket,
                COUNT(*) as count,
                AVG(am.cp_loss) as avg_cp_loss
            FROM analysis_moves am
            JOIN game_index_cache g ON am.game_id = g.game_id
            WHERE am.classification = 3
            {PLAYER_SIDE_FILTER}
        """
        params: list[object] = []
        query = filters.append_to(query, params)
        query += " GROUP BY diff_bucket"

        conn = await self.get_connection()
        async with conn.execute(query, params) as cursor:
            rows = await cursor.fetchall()

        total = sum(row[1] for row in rows)
        bucket_map = {row[0]: row for row in rows}

        by_difficulty = []
        for bucket_key in ("easy", "medium", "hard", "unscored"):
            row = bucket_map.get(bucket_key)
            if not row:
                continue
            count = row[1]
            avg_cp_loss = row[2] or 0.0
            percentage = (count / total * 100) if total > 0 else 0.0
            by_difficulty.append(
                {
                    "difficulty": bucket_key,
                    "count": count,
                    "percentage": round(percentage, 1),
                    "avg_cp_loss": round(float(avg_cp_loss), 1),
                }
            )

        return {
            "total_blunders": total,
            "by_difficulty": by_difficulty,
        }

    async def get_conversion_resilience(
        self,
        filters: StatsFilter | None = None,
    ) -> dict[str, object]:
        filters = filters or StatsFilter()
        query = f"""
            SELECT
                g.game_id,
                g.result,
                g.white,
                g.username,
                am.eval_before,
                am.player
            FROM analysis_moves am
            JOIN game_index_cache g ON am.game_id = g.game_id
            WHERE g.analyzed = 1
            {PLAYER_SIDE_FILTER}
        """
        params: list[object] = []
        query = filters.append_to(query, params)

        conn = await self.get_connection()
        async with conn.execute(query, params) as cursor:
            rows = await cursor.fetchall()

        games: dict[str, dict] = {}
        for game_id, result, white, game_username, eval_before, _player in rows:
            if game_id not in games:
                is_white = white and white.lower() == (game_username or "").lower()
                games[game_id] = {
                    "result": result,
                    "is_white": is_white,
                    "evals": [],
                }

            user_eval = eval_before if games[game_id]["is_white"] else -eval_before
            games[game_id]["evals"].append(user_eval)

        games_with_advantage = 0
        games_converted = 0
        games_with_disadvantage = 0
        games_saved = 0

        for game_data in games.values():
            evals = game_data["evals"]
            if not evals:
                continue

            result = game_data["result"]
            is_white = game_data["is_white"]

            user_won = (result == "1-0" and is_white) or (
                result == "0-1" and not is_white
            )
            user_drew = result == "1/2-1/2"

            peak_advantage = max(evals)
            peak_disadvantage = min(evals)

            if peak_advantage > WINNING_THRESHOLD_CP:
                games_with_advantage += 1
                if user_won:
                    games_converted += 1

            if peak_disadvantage < LOSING_THRESHOLD_CP:
                games_with_disadvantage += 1
                if user_won or user_drew:
                    games_saved += 1

        conversion_rate = (
            round(games_converted / games_with_advantage * 100, 1)
            if games_with_advantage > 0
            else 0.0
        )
        resilience_rate = (
            round(games_saved / games_with_disadvantage * 100, 1)
            if games_with_disadvantage > 0
            else 0.0
        )

        return {
            "conversion_rate": conversion_rate,
            "resilience_rate": resilience_rate,
            "games_with_advantage": games_with_advantage,
            "games_converted": games_converted,
            "games_with_disadvantage": games_with_disadvantage,
            "games_saved": games_saved,
        }

    async def get_collapse_point(
        self,
        filters: StatsFilter | None = None,
    ) -> dict[str, object]:
        filters = filters or StatsFilter()
        query = f"""
            SELECT
                am.game_id,
                am.move_number
            FROM analysis_moves am
            JOIN game_index_cache g ON am.game_id = g.game_id
            WHERE g.analyzed = 1
              AND am.classification = 3
            {PLAYER_SIDE_FILTER}
        """
        params: list[object] = []
        query = filters.append_to(query, params)
        query += " ORDER BY am.game_id, am.ply"

        conn = await self.get_connection()
        async with conn.execute(query, params) as cursor:
            blunder_rows = await cursor.fetchall()

        first_blunder_by_game: dict[str, int] = {}
        for game_id, move_number in blunder_rows:
            if game_id not in first_blunder_by_game:
                first_blunder_by_game[game_id] = move_number

        total_query = """
            SELECT COUNT(*)
            FROM game_index_cache g
            WHERE g.analyzed = 1
        """
        total_params: list[object] = []
        total_query = filters.append_to(total_query, total_params, include_phase=False)

        async with conn.execute(total_query, total_params) as cursor:
            total_row = await cursor.fetchone()
        total_analyzed = total_row[0] if total_row else 0

        collapse_moves = list(first_blunder_by_game.values())
        total_with_blunders = len(collapse_moves)
        total_without_blunders = total_analyzed - total_with_blunders

        if not collapse_moves:
            return {
                "avg_collapse_move": None,
                "median_collapse_move": None,
                "distribution": [],
                "total_games_with_blunders": 0,
                "total_games_without_blunders": total_without_blunders,
            }

        avg_move = round(statistics.mean(collapse_moves))
        median_move = round(statistics.median(collapse_moves))

        bucket_counts: dict[str, int] = {}
        for move in collapse_moves:
            if move >= COLLAPSE_MAX_BUCKET_START:
                label = f"{COLLAPSE_MAX_BUCKET_START}+"
            else:
                start = ((move - 1) // COLLAPSE_BUCKET_SIZE) * COLLAPSE_BUCKET_SIZE + 1
                end = start + COLLAPSE_BUCKET_SIZE - 1
                label = f"{start}-{end}"
            bucket_counts[label] = bucket_counts.get(label, 0) + 1

        def bucket_sort_key(label: str) -> int:
            return int(label.split("-")[0].rstrip("+"))

        distribution = [
            {"move_range": label, "count": count}
            for label, count in sorted(
                bucket_counts.items(), key=lambda x: bucket_sort_key(x[0])
            )
        ]

        return {
            "avg_collapse_move": avg_move,
            "median_collapse_move": median_move,
            "distribution": distribution,
            "total_games_with_blunders": total_with_blunders,
            "total_games_without_blunders": total_without_blunders,
        }

    async def get_growth_metrics(
        self,
        filters: StatsFilter | None = None,
    ) -> list[dict[str, object]]:
        filters = filters or StatsFilter()
        query = f"""
            SELECT
                g.game_id,
                g.end_time_utc,
                COUNT(CASE WHEN am.classification = 3 THEN 1 END) as blunder_count,
                AVG(am.cp_loss) as avg_cpl,
                AVG(CASE WHEN am.classification = 3 THEN am.cp_loss END) as avg_blunder_cpl,
                COUNT(CASE WHEN am.classification = 3 AND am.cp_loss > {CATASTROPHIC_CP_LOSS} THEN 1 END) as catastrophic_count,
                COUNT(CASE WHEN am.classification = 3 THEN 1 END) as total_blunders_for_rate
            FROM analysis_moves am
            JOIN game_index_cache g ON am.game_id = g.game_id
            WHERE g.analyzed = 1
            {PLAYER_SIDE_FILTER}
        """
        params: list[object] = []
        query = filters.append_to(query, params, include_phase=False)
        query += " GROUP BY g.game_id, g.end_time_utc ORDER BY g.end_time_utc ASC"

        conn = await self.get_connection()
        async with conn.execute(query, params) as cursor:
            rows = await cursor.fetchall()

        return [
            {
                "game_id": row[0],
                "end_time_utc": row[1],
                "blunder_count": row[2],
                "avg_cpl": round(float(row[3]), 1) if row[3] is not None else 0.0,
                "avg_blunder_cpl": round(float(row[4]), 1)
                if row[4] is not None
                else 0.0,
                "catastrophic_count": row[5],
                "total_blunders": row[6],
            }
            for row in rows
        ]
