from __future__ import annotations

import dataclasses
import statistics
from collections import defaultdict
from collections.abc import Iterable

from blunder_tutor.analysis.tactics import PATTERN_LABELS
from blunder_tutor.constants import COLOR_LABELS, PHASE_LABELS
from blunder_tutor.repositories.base import BaseDbRepository
from blunder_tutor.utils.accuracy import game_accuracy
from blunder_tutor.utils.time_control import GAME_TYPE_LABELS

CATASTROPHIC_CP_LOSS = 500
WINNING_THRESHOLD_CP = 200
LOSING_THRESHOLD_CP = -200

COLLAPSE_BUCKET_SIZE = 5
COLLAPSE_MAX_BUCKET_START = 41

type _AggregationResult = tuple[int, list[dict[str, object]]]
type _EcoStats = list[tuple[tuple[str, str], dict[str, object]]]
type _BucketLossMap = dict[tuple[str, object], list[int]]


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
        criteria = filters or StatsFilter()  # noqa: WPS204 — coerce None to default; opt-arg pattern is the canonical entry-point shape across stats methods.
        game_params: list[object] = []
        game_where = criteria.append_to("WHERE 1=1", game_params, include_phase=False)

        game_row = await self._fetch_one(
            f"""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN analyzed = 1 THEN 1 ELSE 0 END) as analyzed
            FROM game_index_cache g
            {game_where}
            """,
            game_params,
        )
        total_games = game_row["total"] if game_row else 0
        analyzed_games = _safe_int(game_row["analyzed"]) if game_row else 0

        blunder_params: list[object] = []
        blunder_where = criteria.append_to(
            f"WHERE am.classification = 3 {PLAYER_SIDE_FILTER}",
            blunder_params,
        )
        blunder_row = await self._fetch_one(
            f"""
            SELECT COUNT(*)
            FROM analysis_moves am
            JOIN game_index_cache g ON am.game_id = g.game_id
            {blunder_where}
            """,
            blunder_params,
        )
        total_blunders = blunder_row[0] if blunder_row else 0

        return {
            "total_games": total_games,
            "analyzed_games": analyzed_games,
            "total_blunders": total_blunders,
            "pending_analysis": total_games - analyzed_games,
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

        rows = await self._fetch_rows(query, params)
        return [
            {
                "source": row["source"],
                "username": row["username"],
                "total_games": row["total_games"],
                "analyzed_games": _safe_int(row["analyzed_games"]),
                "pending_games": row["total_games"] - _safe_int(row["analyzed_games"]),
                "oldest_game_date": row["oldest_game_date"],
                "newest_game_date": row["newest_game_date"],
            }
            for row in rows
        ]

    async def get_blunder_breakdown(
        self,
        filters: StatsFilter | None = None,
    ) -> dict[str, object]:
        criteria = filters or StatsFilter()
        params: list[object] = []
        query = criteria.append_to(
            f"""
            SELECT
                COUNT(*) as total_blunders,
                AVG(am.cp_loss) as avg_cp_loss
            FROM analysis_moves am
            JOIN game_index_cache g ON am.game_id = g.game_id
            WHERE am.classification = 3
            {PLAYER_SIDE_FILTER}
            """,
            params,
        )
        row = await self._fetch_one(query, params)
        total_blunders = row["total_blunders"] if row else 0
        avg_cp_loss = row["avg_cp_loss"] if row else 0.0

        date_params: list[object] = []
        date_query = criteria.append_to(
            f"""
            SELECT
                DATE(g.end_time_utc) as date,
                COUNT(*) as count
            FROM analysis_moves am
            JOIN game_index_cache g ON am.game_id = g.game_id
            WHERE am.classification = 3
            AND g.end_time_utc IS NOT NULL
            {PLAYER_SIDE_FILTER}
            """,
            date_params,
        )
        date_query += " GROUP BY DATE(g.end_time_utc) ORDER BY date DESC LIMIT 30"
        date_rows = await self._fetch_rows(date_query, date_params)

        return {
            "total_blunders": total_blunders,
            "avg_cp_loss": float(avg_cp_loss) if avg_cp_loss else 0.0,
            "blunders_by_date": [
                {"date": row["date"], "count": row["count"]} for row in date_rows
            ],
        }

    async def get_analysis_progress(self) -> dict[str, object]:
        row = await self._fetch_one(
            """
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
                SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed,
                SUM(CASE WHEN status = 'in_progress' THEN 1 ELSE 0 END) as in_progress
            FROM background_jobs
            """,
            [],
        )
        if not row:
            return {
                "total_jobs": 0,
                "completed_jobs": 0,
                "failed_jobs": 0,
                "in_progress_jobs": 0,
            }
        return {
            "total_jobs": row["total"],
            "completed_jobs": _safe_int(row["completed"]),
            "failed_jobs": _safe_int(row["failed"]),
            "in_progress_jobs": _safe_int(row["in_progress"]),
        }

    async def get_recent_activity(self, limit: int = 10) -> list[dict[str, object]]:
        rows = await self._fetch_rows(
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
            [limit],
        )
        return [dict(row) for row in rows]

    async def get_blunders_by_phase(
        self,
        filters: StatsFilter | None = None,
    ) -> dict[str, object]:
        rows = await self._fetch_aggregation(
            "game_phase, COUNT(*) as count, AVG(cp_loss) as avg_cp_loss",
            "GROUP BY game_phase ORDER BY game_phase",
            filters or StatsFilter(),
        )
        total, phases = _bucket_aggregation(
            rows, "game_phase", PHASE_LABELS,
            label_field="phase", id_field="phase_id",
        )
        return {"total_blunders": total, "by_phase": phases}

    async def get_blunders_by_eco(
        self,
        filters: StatsFilter | None = None,
        limit: int = 10,
    ) -> dict[str, object]:
        criteria = filters or StatsFilter()
        params: list[object] = []
        query = criteria.append_to(
            f"""
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
            """,
            params,
        )
        rows = await self._fetch_rows(query, params)
        sorted_ecos = _aggregate_eco_rows(rows, limit)
        total = sum(stats["count"] for _, stats in sorted_ecos)
        return {
            "total_blunders": total,
            "by_opening": [
                _eco_entry(eco_code, eco_name, stats, total)
                for (eco_code, eco_name), stats in sorted_ecos
            ],
        }

    async def get_blunders_by_color(
        self,
        filters: StatsFilter | None = None,
    ) -> dict[str, object]:
        criteria = filters or StatsFilter()
        rows = await self._fetch_aggregation(
            """
            CASE
                WHEN LOWER(g.white) = LOWER(g.username) THEN 0
                WHEN LOWER(g.black) = LOWER(g.username) THEN 1
            END as user_color,
            COUNT(*) as count,
            AVG(am.cp_loss) as avg_cp_loss
            """,
            "GROUP BY user_color ORDER BY user_color",
            criteria,
        )
        total, colors = _bucket_aggregation(
            rows, "user_color", COLOR_LABELS,
            label_field="color", id_field="color_id",
        )

        date_params: list[object] = []
        date_query = criteria.append_to(
            f"""
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
            """,
            date_params,
        )
        date_query += " GROUP BY date, user_color ORDER BY date DESC LIMIT 60"
        date_rows = await self._fetch_rows(date_query, date_params)

        return {
            "total_blunders": total,
            "by_color": colors,
            "blunders_by_date": [
                {
                    "date": row["date"],
                    "color": COLOR_LABELS.get(row["user_color"], "unknown"),
                    "count": row["count"],
                }
                for row in date_rows
            ],
        }

    async def get_games_by_date(
        self,
        filters: StatsFilter | None = None,
    ) -> list[dict[str, object]]:
        criteria = filters or StatsFilter()
        params: list[object] = []
        query = criteria.append_to(
            f"""
            SELECT
                g.game_id,
                DATE(g.end_time_utc) as game_date,
                am.cp_loss
            FROM analysis_moves am
            JOIN game_index_cache g ON am.game_id = g.game_id
            WHERE g.analyzed = 1
            {PLAYER_SIDE_FILTER}
            """,
            params,
        )
        query += " ORDER BY game_date ASC"
        rows = await self._fetch_rows(query, params)
        date_accuracies = _accuracies_by_bucket(rows)
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
        criteria = filters or StatsFilter()
        params: list[object] = []
        query = criteria.append_to(
            f"""
            SELECT
                g.game_id,
                CAST(strftime('%H', g.end_time_utc) AS INTEGER) as hour,
                am.cp_loss
            FROM analysis_moves am
            JOIN game_index_cache g ON am.game_id = g.game_id
            WHERE g.analyzed = 1
            {PLAYER_SIDE_FILTER}
            """,
            params,
        )
        rows = await self._fetch_rows(query, params)
        hour_accuracies = _accuracies_by_bucket(rows)
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
        rows = await self._fetch_aggregation(
            "tactical_pattern, COUNT(*) as count, AVG(cp_loss) as avg_cp_loss",
            "GROUP BY tactical_pattern ORDER BY count DESC",
            filters or StatsFilter(),
        )
        total = sum(row["count"] for row in rows)
        return {
            "total_blunders": total,
            "by_pattern": [_pattern_entry(row, total) for row in rows],
        }

    async def get_blunders_by_game_type(
        self,
        filters: StatsFilter | None = None,
    ) -> dict[str, object]:
        rows = await self._fetch_aggregation(
            "g.game_type, COUNT(*) as count, AVG(am.cp_loss) as avg_cp_loss",
            "GROUP BY g.game_type ORDER BY g.game_type",
            filters or StatsFilter(),
        )
        total, game_types = _bucket_aggregation(
            rows, "game_type", GAME_TYPE_LABELS,
            label_field="game_type", id_field="game_type_id",
        )
        # game_type historically uses -1 as the sentinel id for the
        # "no game_type recorded" bucket (other report endpoints pass None).
        for entry in game_types:
            if entry["game_type_id"] is None:
                entry["game_type_id"] = -1
        return {"total_blunders": int(total), "by_game_type": game_types}

    async def get_blunders_by_phase_filtered(
        self,
        filters: StatsFilter | None = None,
        player_colors: list[int] | None = None,
    ) -> dict[str, object]:
        criteria = filters or StatsFilter()
        params: list[object] = []
        query = criteria.append_to(
            f"""
            SELECT
                am.game_phase,
                COUNT(*) as count,
                AVG(am.cp_loss) as avg_cp_loss
            FROM analysis_moves am
            JOIN game_index_cache g ON am.game_id = g.game_id
            WHERE am.classification = 3
            {PLAYER_SIDE_FILTER}
            """,
            params,
        )
        if player_colors:
            placeholders = ",".join("?" * len(player_colors))
            query += f" AND am.player IN ({placeholders})"
            params.extend(player_colors)
        query += " GROUP BY am.game_phase ORDER BY am.game_phase"

        rows = await self._fetch_rows(query, params)
        total, phases = _bucket_aggregation(
            rows, "game_phase", PHASE_LABELS,
            label_field="phase", id_field="phase_id",
        )
        return {"total_blunders": total, "by_phase": phases}

    async def get_blunders_by_difficulty(
        self,
        filters: StatsFilter | None = None,
    ) -> dict[str, object]:
        criteria = filters or StatsFilter()
        params: list[object] = []
        query = criteria.append_to(
            f"""
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
            """,
            params,
        )
        query += " GROUP BY diff_bucket"

        rows = await self._fetch_rows(query, params)
        total = sum(row["count"] for row in rows)
        bucket_map = {row["diff_bucket"]: row for row in rows}

        return {
            "total_blunders": total,
            "by_difficulty": [
                _difficulty_entry(bucket_key, bucket_map[bucket_key], total)
                for bucket_key in ("easy", "medium", "hard", "unscored")
                if bucket_key in bucket_map
            ],
        }

    async def get_conversion_resilience(
        self,
        filters: StatsFilter | None = None,
    ) -> dict[str, object]:
        criteria = filters or StatsFilter()
        params: list[object] = []
        query = criteria.append_to(
            f"""
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
            """,
            params,
        )
        rows = await self._fetch_rows(query, params)
        games = _aggregate_game_evals(rows)
        outcomes = _count_conversion_outcomes(games.values())
        return {
            **outcomes,
            "conversion_rate": _safe_rate(
                outcomes["games_converted"], outcomes["games_with_advantage"],
            ),
            "resilience_rate": _safe_rate(
                outcomes["games_saved"], outcomes["games_with_disadvantage"],
            ),
        }

    async def get_collapse_point(
        self,
        filters: StatsFilter | None = None,
    ) -> dict[str, object]:
        criteria = filters or StatsFilter()
        params: list[object] = []
        query = criteria.append_to(
            f"""
            SELECT
                am.game_id,
                am.move_number
            FROM analysis_moves am
            JOIN game_index_cache g ON am.game_id = g.game_id
            WHERE g.analyzed = 1
              AND am.classification = 3
            {PLAYER_SIDE_FILTER}
            """,
            params,
        )
        query += " ORDER BY am.game_id, am.ply"
        blunder_rows = await self._fetch_rows(query, params)
        collapse_moves = list(_first_blunder_per_game(blunder_rows).values())

        total_params: list[object] = []
        total_query = criteria.append_to(
            "SELECT COUNT(*) FROM game_index_cache g WHERE g.analyzed = 1",
            total_params,
            include_phase=False,
        )
        total_row = await self._fetch_one(total_query, total_params)
        total_analyzed = total_row[0] if total_row else 0
        total_without_blunders = total_analyzed - len(collapse_moves)

        if not collapse_moves:
            return {
                "avg_collapse_move": None,
                "median_collapse_move": None,
                "distribution": [],
                "total_games_with_blunders": 0,
                "total_games_without_blunders": total_without_blunders,
            }

        return {
            "avg_collapse_move": round(statistics.mean(collapse_moves)),
            "median_collapse_move": round(statistics.median(collapse_moves)),
            "distribution": _collapse_distribution(collapse_moves),
            "total_games_with_blunders": len(collapse_moves),
            "total_games_without_blunders": total_without_blunders,
        }

    async def get_growth_metrics(
        self,
        filters: StatsFilter | None = None,
    ) -> list[dict[str, object]]:
        criteria = filters or StatsFilter()
        params: list[object] = []
        query = criteria.append_to(
            f"""
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
            """,
            params,
            include_phase=False,
        )
        query += " GROUP BY g.game_id, g.end_time_utc ORDER BY g.end_time_utc ASC"
        rows = await self._fetch_rows(query, params)
        return [_growth_entry(row) for row in rows]

    async def _fetch_rows(
        self, query: str, params: list[object],
    ) -> list[dict[str, object]]:
        conn = await self.get_connection()
        async with conn.execute(query, params) as cursor:
            return await cursor.fetchall()

    async def _fetch_one(
        self, query: str, params: list[object],
    ) -> dict[str, object] | None:
        conn = await self.get_connection()
        async with conn.execute(query, params) as cursor:
            return await cursor.fetchone()

    async def _fetch_aggregation(
        self,
        select_columns: str,
        group_order_clause: str,
        criteria: StatsFilter,
    ) -> list[dict[str, object]]:
        params: list[object] = []
        query = criteria.append_to(
            f"""
            SELECT
                {select_columns}
            FROM analysis_moves am
            JOIN game_index_cache g ON am.game_id = g.game_id
            WHERE am.classification = 3
            {PLAYER_SIDE_FILTER}
            """,
            params,
        )
        query += f" {group_order_clause}"
        return await self._fetch_rows(query, params)


def _safe_int(value: object) -> int:
    return int(value) if value is not None else 0


def _safe_rate(numerator: int, denominator: int) -> float:
    return round(numerator / denominator * 100, 1) if denominator > 0 else 0.0


def _bucket_aggregation(
    rows: list[dict[str, object]],
    id_key: str,
    label_map: dict[int, str],
    *,
    label_field: str,
    id_field: str,
    default_label: str = "unknown",
) -> _AggregationResult:
    total = sum(row["count"] for row in rows)
    entries = [
        _bucket_entry(row, id_key, label_map, label_field, id_field, default_label, total)
        for row in rows
    ]
    return total, entries


def _bucket_entry(
    row: dict[str, object],
    id_key: str,
    label_map: dict[int, str],
    label_field: str,
    id_field: str,
    default_label: str,
    total: int,
) -> dict[str, object]:
    bucket_int = row[id_key]
    count = row["count"]
    return {
        label_field: label_map.get(bucket_int, default_label),
        id_field: bucket_int,
        "count": count,
        "percentage": _safe_pct(count, total),
        "avg_cp_loss": _round_or_zero(row["avg_cp_loss"]),
    }


def _safe_pct(numerator: int, total: int) -> float:
    return round(numerator / total * 100, 1) if total > 0 else 0.0


def _aggregate_eco_rows(rows: list[dict[str, object]], limit: int) -> _EcoStats:
    eco_stats: dict[tuple[str, str], dict[str, object]] = {}
    for row in rows:
        key = (row["eco_code"], row["eco_name"])
        bucket = eco_stats.setdefault(
            key, {"count": 0, "total_cp_loss": 0.0, "game_ids": set()},
        )
        bucket["count"] += 1
        bucket["total_cp_loss"] += row["cp_loss"] or 0
        bucket["game_ids"].add(row["game_id"])
    sorted_items = sorted(eco_stats.items(), key=_eco_count_key, reverse=True)
    return sorted_items[:limit]


def _eco_count_key(item: tuple[tuple[str, str], dict[str, object]]) -> int:
    return item[1]["count"]


def _eco_entry(
    eco_code: str, eco_name: str, stats: dict[str, object], total: int,
) -> dict[str, object]:
    count = stats["count"]
    avg_cp_loss = stats["total_cp_loss"] / count if count > 0 else 0.0
    percentage = (count / total * 100) if total > 0 else 0.0
    return {
        "eco_code": eco_code,
        "eco_name": eco_name,
        "count": count,
        "percentage": round(percentage, 1),
        "avg_cp_loss": round(float(avg_cp_loss), 1),
        "game_count": len(stats["game_ids"]),
    }


def _pattern_entry(row: dict[str, object], total: int) -> dict[str, object]:
    pattern_int = row["tactical_pattern"]
    label = (
        PATTERN_LABELS.get(pattern_int, "Unknown")
        if pattern_int is not None
        else "Not Classified"
    )
    count = row["count"]
    return {
        "pattern": label,
        "pattern_id": pattern_int,
        "count": count,
        "percentage": _safe_pct(count, total),
        "avg_cp_loss": _round_or_zero(row["avg_cp_loss"]),
    }


def _difficulty_entry(
    bucket_key: str, row: dict[str, object], total: int,
) -> dict[str, object]:
    count = row["count"]
    avg_cp_loss = row["avg_cp_loss"] or 0.0
    percentage = (count / total * 100) if total > 0 else 0.0
    return {
        "difficulty": bucket_key,
        "count": count,
        "percentage": round(percentage, 1),
        "avg_cp_loss": round(float(avg_cp_loss), 1),
    }


def _accuracies_by_bucket(
    rows: list[tuple[str, object, int]],
) -> dict[object, list[float]]:
    """Group rows by (game_id, bucket), collapse cp_losses to per-game accuracy, then bucket by their second key."""
    game_bucket_losses: _BucketLossMap = defaultdict(list)
    for game_id, bucket_key, cp_loss in rows:
        game_bucket_losses[(game_id, bucket_key)].append(cp_loss)

    bucket_accuracies: dict[object, list[float]] = defaultdict(list)
    for (_game_id, bucket_key), losses in game_bucket_losses.items():
        bucket_accuracies[bucket_key].append(game_accuracy(losses))
    return bucket_accuracies


def _aggregate_game_evals(
    rows: Iterable[tuple[str, str, str, str, int, int]],
) -> dict[str, dict[str, object]]:
    games: dict[str, dict[str, object]] = {}
    for game_id, game_result, white, game_username, eval_before, _player in rows:
        if game_id not in games:
            is_white = bool(white) and white.lower() == (game_username or "").lower()
            games[game_id] = {"result": game_result, "is_white": is_white, "evals": []}
        bucket = games[game_id]
        user_eval = eval_before if bucket["is_white"] else -eval_before
        bucket["evals"].append(user_eval)
    return games


def _count_conversion_outcomes(
    games: Iterable[dict[str, object]],
) -> dict[str, int]:
    counts = {
        "games_with_advantage": 0,
        "games_converted": 0,
        "games_with_disadvantage": 0,
        "games_saved": 0,
    }
    for game in games:
        flags = _classify_game_outcome(game)
        if flags is None:
            continue
        had_advantage, converted, had_disadvantage, saved = flags
        counts["games_with_advantage"] += had_advantage
        counts["games_converted"] += converted
        counts["games_with_disadvantage"] += had_disadvantage
        counts["games_saved"] += saved
    return counts


def _classify_game_outcome(
    game: dict[str, object],
) -> tuple[bool, bool, bool, bool] | None:
    evals = game["evals"]
    if not evals:
        return None

    result = game["result"]
    is_white = game["is_white"]
    user_won = (  # noqa: WPS408 — complementary, not duplicate: white-wins-as-white OR black-wins-as-black.
        result == "1-0" and is_white
    ) or (result == "0-1" and not is_white)
    user_drew = result == "1/2-1/2"

    had_advantage = max(evals) > WINNING_THRESHOLD_CP
    had_disadvantage = min(evals) < LOSING_THRESHOLD_CP
    return (
        had_advantage,
        had_advantage and user_won,
        had_disadvantage,
        had_disadvantage and (user_won or user_drew),
    )


def _first_blunder_per_game(
    rows: Iterable[tuple[str, int]],
) -> dict[str, int]:
    first_by_game: dict[str, int] = {}
    for game_id, move_number in rows:
        if game_id not in first_by_game:
            first_by_game[game_id] = move_number
    return first_by_game


def _collapse_distribution(moves: list[int]) -> list[dict[str, object]]:
    bucket_counts: dict[str, int] = {}
    for move in moves:
        if move >= COLLAPSE_MAX_BUCKET_START:
            label = f"{COLLAPSE_MAX_BUCKET_START}+"
        else:
            start = ((move - 1) // COLLAPSE_BUCKET_SIZE) * COLLAPSE_BUCKET_SIZE + 1
            label = f"{start}-{start + COLLAPSE_BUCKET_SIZE - 1}"
        bucket_counts[label] = bucket_counts.get(label, 0) + 1
    return [
        {"move_range": label, "count": count}
        for label, count in sorted(bucket_counts.items(), key=_bucket_sort_key)
    ]


def _bucket_sort_key(item: tuple[str, int]) -> int:
    return int(item[0].split("-")[0].rstrip("+"))


def _growth_entry(row: dict[str, object]) -> dict[str, object]:
    return {
        "game_id": row["game_id"],
        "end_time_utc": row["end_time_utc"],
        "blunder_count": row["blunder_count"],
        "avg_cpl": _round_or_zero(row["avg_cpl"]),
        "avg_blunder_cpl": _round_or_zero(row["avg_blunder_cpl"]),
        "catastrophic_count": row["catastrophic_count"],
        "total_blunders": row["total_blunders_for_rate"],
    }


def _round_or_zero(value: object) -> float:
    return round(float(value), 1) if value is not None else 0.0
