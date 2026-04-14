from __future__ import annotations

from datetime import date
from typing import Annotated, Any

from fastapi import Depends, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.routing import APIRouter
from pydantic import BaseModel, Field, field_validator

from blunder_tutor.cache.decorator import cached
from blunder_tutor.constants import PHASE_FROM_STRING
from blunder_tutor.repositories.stats_repository import StatsFilter
from blunder_tutor.utils.time_control import GAME_TYPE_FROM_STRING
from blunder_tutor.web.dependencies import (
    PuzzleAttemptRepoDep,
    StatsRepoDep,
    set_request_username,
)


def _parse_string_list(
    values: list[str] | None, mapping: dict[str, int]
) -> list[int] | None:
    if not values:
        return None
    ids = [mapping.get(v.lower()) for v in values]
    filtered = [v for v in ids if v is not None]
    return filtered or None


def _build_stats_filter(
    start_date: Annotated[
        date | None,
        Query(description="Start date for filtering (YYYY-MM-DD)"),
    ] = None,
    end_date: Annotated[
        date | None,
        Query(description="End date for filtering (YYYY-MM-DD)"),
    ] = None,
    game_types: Annotated[
        list[str] | None,
        Query(description="Filter by game types (bullet, blitz, rapid, classical)"),
    ] = None,
    game_phases: Annotated[
        list[str] | None,
        Query(description="Filter by game phases (opening, middlegame, endgame)"),
    ] = None,
) -> StatsFilter:
    return StatsFilter(
        start_date=start_date.isoformat() if start_date else None,
        end_date=end_date.isoformat() if end_date else None,
        game_types=_parse_string_list(game_types, GAME_TYPE_FROM_STRING),
        game_phases=_parse_string_list(game_phases, PHASE_FROM_STRING),
    )


StatsFilterDep = Annotated[StatsFilter, Depends(_build_stats_filter)]


class DashboardStats(BaseModel):
    total_games: int = Field(description="Total number of games")
    analyzed_games: int = Field(description="Number of analyzed games")
    total_blunders: int = Field(description="Total blunders found")
    pending_analysis: int = Field(description="Games pending analysis")


class GameBreakdown(BaseModel):
    items: list[dict[str, Any]] = Field(
        description="List of game statistics grouped by criteria"
    )


class BlunderBreakdown(BaseModel):
    total_blunders: int = Field(description="Total number of blunders")
    avg_cp_loss: float = Field(description="Average centipawn loss")
    blunders_by_date: list[dict[str, Any]] = Field(
        description="Blunders grouped by date"
    )


class AnalysisProgress(BaseModel):
    total_jobs: int = Field(description="Total number of analysis jobs")
    completed_jobs: int = Field(description="Completed analysis jobs")
    failed_jobs: int = Field(description="Failed analysis jobs")
    in_progress_jobs: int = Field(description="Jobs currently in progress")


class TrainingStats(BaseModel):
    total_attempts: int = Field(description="Total puzzle attempts")
    correct_attempts: int = Field(description="Correct puzzle attempts")
    incorrect_attempts: int = Field(description="Incorrect puzzle attempts")
    unique_puzzles: int = Field(description="Unique puzzles attempted")
    accuracy: float = Field(description="Success rate (0.0 to 1.0)")


class PhaseBlunderItem(BaseModel):
    phase: str = Field(description="Game phase name (opening, middlegame, endgame)")
    phase_id: int | None = Field(description="Game phase ID")
    count: int = Field(description="Number of blunders in this phase")
    percentage: float = Field(description="Percentage of total blunders")
    avg_cp_loss: float = Field(description="Average centipawn loss for this phase")


class BlundersByPhase(BaseModel):
    total_blunders: int = Field(description="Total number of blunders")
    by_phase: list[PhaseBlunderItem] = Field(
        description="Blunders grouped by game phase"
    )


class ECOBlunderItem(BaseModel):
    eco_code: str = Field(description="ECO opening code (e.g., B20, C50)")
    eco_name: str = Field(description="Opening name")
    count: int = Field(description="Number of blunders in this opening")
    percentage: float = Field(description="Percentage of total blunders")
    avg_cp_loss: float = Field(description="Average centipawn loss")
    game_count: int = Field(description="Number of games with this opening")


class BlundersByECO(BaseModel):
    total_blunders: int = Field(description="Total number of blunders")
    by_opening: list[ECOBlunderItem] = Field(
        description="Blunders grouped by ECO opening code"
    )


class ColorBlunderItem(BaseModel):
    color: str = Field(description="Player color (white or black)")
    color_id: int | None = Field(description="Color ID (0=white, 1=black)")
    count: int = Field(description="Number of blunders when playing this color")
    percentage: float = Field(description="Percentage of total blunders")
    avg_cp_loss: float = Field(description="Average centipawn loss")


class ColorDateBlunderItem(BaseModel):
    date: str = Field(description="Date (YYYY-MM-DD)")
    color: str = Field(description="Player color (white or black)")
    count: int = Field(description="Number of blunders on this date with this color")


class BlundersByColor(BaseModel):
    total_blunders: int = Field(description="Total number of blunders by the user")
    by_color: list[ColorBlunderItem] = Field(
        description="Blunders grouped by player color"
    )
    blunders_by_date: list[ColorDateBlunderItem] = Field(
        description="Blunders grouped by date and color"
    )


class DailyActivityItem(BaseModel):
    total: int = Field(description="Total puzzle attempts")
    correct: int = Field(description="Correct attempts")
    incorrect: int = Field(description="Incorrect attempts")


class ActivityHeatmapResponse(BaseModel):
    daily_counts: dict[str, DailyActivityItem] = Field(
        description="Puzzle attempts per day (date string -> {total, correct, incorrect})"
    )
    max_count: int = Field(description="Maximum daily count for scaling")
    total_days: int = Field(description="Number of days with activity")
    total_attempts: int = Field(description="Total attempts in period")


class GrowthWindow(BaseModel):
    window_index: int = Field(description="Window index (0 = oldest)")
    game_start: int = Field(description="1-based index of first game in window")
    game_end: int = Field(description="1-based index of last game in window")
    avg_blunders_per_game: float = Field(description="Average blunders per game")
    avg_cpl: float = Field(description="Average centipawn loss per game")
    avg_blunder_severity: float = Field(description="Average CPL of blunders only")
    clean_game_rate: float = Field(description="Percentage of games with 0 blunders")
    catastrophic_rate: float = Field(
        description="Percentage of blunders with CPL > 500"
    )


class GrowthTrend(BaseModel):
    blunder_frequency: str = Field(description="improving / stable / declining")
    move_quality: str = Field(description="improving / stable / declining")
    severity: str = Field(description="improving / stable / declining")
    clean_rate: str = Field(description="improving / stable / declining")
    catastrophic_rate: str = Field(description="improving / stable / declining")

    @field_validator(
        "blunder_frequency",
        "move_quality",
        "severity",
        "clean_rate",
        "catastrophic_rate",
    )
    @classmethod
    def validate_direction(cls, v: str) -> str:
        if v not in ("improving", "stable", "declining"):
            msg = "Must be improving, stable, or declining"
            raise ValueError(msg)
        return v


class GrowthMetricsResponse(BaseModel):
    windows: list[GrowthWindow] = Field(description="Rolling window metrics")
    trend: GrowthTrend | None = Field(description="Trend comparing last two windows")
    total_games: int = Field(description="Total analyzed games")
    window_size: int = Field(description="Games per window")


TREND_THRESHOLD = 0.05


def _compute_growth_windows(
    per_game: list[dict], window_size: int
) -> list[GrowthWindow]:
    windows = []
    for i in range(0, len(per_game) - window_size + 1, window_size):
        chunk = per_game[i : i + window_size]
        total_blunders = sum(g["blunder_count"] for g in chunk)
        total_catastrophic = sum(g["catastrophic_count"] for g in chunk)
        clean_games = sum(1 for g in chunk if g["blunder_count"] == 0)

        windows.append(
            GrowthWindow(
                window_index=len(windows),
                game_start=i + 1,
                game_end=i + len(chunk),
                avg_blunders_per_game=round(total_blunders / len(chunk), 2),
                avg_cpl=round(sum(g["avg_cpl"] for g in chunk) / len(chunk), 1),
                avg_blunder_severity=round(
                    (
                        sum(
                            g["avg_blunder_cpl"]
                            for g in chunk
                            if g["avg_blunder_cpl"] > 0
                        )
                        / max(sum(1 for g in chunk if g["avg_blunder_cpl"] > 0), 1)
                    ),
                    1,
                ),
                clean_game_rate=round(clean_games / len(chunk) * 100, 1),
                catastrophic_rate=round(
                    total_catastrophic / max(total_blunders, 1) * 100, 1
                ),
            )
        )
    return windows


def _trend_direction(old: float, new: float, *, lower_is_better: bool) -> str:
    if old == 0:
        return "stable"
    change = (new - old) / abs(old)
    if lower_is_better:
        change = -change
    if change > TREND_THRESHOLD:
        return "improving"
    if change < -TREND_THRESHOLD:
        return "declining"
    return "stable"


def _compute_trend(windows: list[GrowthWindow]) -> GrowthTrend | None:
    if len(windows) < 2:
        return None
    prev, last = windows[-2], windows[-1]
    return GrowthTrend(
        blunder_frequency=_trend_direction(
            prev.avg_blunders_per_game, last.avg_blunders_per_game, lower_is_better=True
        ),
        move_quality=_trend_direction(prev.avg_cpl, last.avg_cpl, lower_is_better=True),
        severity=_trend_direction(
            prev.avg_blunder_severity, last.avg_blunder_severity, lower_is_better=True
        ),
        clean_rate=_trend_direction(
            prev.clean_game_rate, last.clean_game_rate, lower_is_better=False
        ),
        catastrophic_rate=_trend_direction(
            prev.catastrophic_rate, last.catastrophic_rate, lower_is_better=True
        ),
    )


stats_router = APIRouter(dependencies=[Depends(set_request_username)])


@stats_router.get(
    "/api/stats",
    response_model=DashboardStats,
    summary="Get dashboard statistics",
    description="Returns overall dashboard statistics including total games, analyzed games, blunders, and pending analysis.",
)
@cached(tag="stats", ttl=300, version=1, key_params=["filters"])
async def get_dashboard_stats(
    request: Request,
    stats_repo: StatsRepoDep,
    filters: StatsFilterDep,
) -> dict[str, Any]:
    return await stats_repo.get_overview_stats(filters=filters)


@stats_router.get(
    "/api/stats/games",
    response_model=GameBreakdown,
    summary="Get game breakdown",
    description="Returns game statistics grouped by source and/or username with optional filtering.",
)
@cached(tag="stats", ttl=300, version=1, key_params=["source"])
async def get_game_breakdown(
    request: Request,
    stats_repo: StatsRepoDep,
    source: Annotated[
        str | None,
        Query(description="Filter by game source (e.g., 'lichess', 'chesscom')"),
    ] = None,
) -> dict[str, Any]:
    breakdown = await stats_repo.get_game_breakdown(source=source)
    return {"items": breakdown}


@stats_router.get(
    "/api/stats/blunders",
    response_model=BlunderBreakdown,
    summary="Get blunder breakdown",
    description="Returns blunder statistics with optional filtering by date range.",
)
@cached(tag="stats", ttl=300, version=1, key_params=["filters"])
async def get_blunder_breakdown(
    request: Request,
    stats_repo: StatsRepoDep,
    filters: StatsFilterDep,
) -> dict[str, Any]:
    return await stats_repo.get_blunder_breakdown(filters=filters)


@stats_router.get(
    "/api/stats/progress",
    response_model=AnalysisProgress,
    summary="Get analysis progress",
    description="Returns metrics about analysis job progress including completed, failed, and in-progress jobs.",
)
async def get_analysis_progress(stats_repo: StatsRepoDep) -> dict[str, Any]:
    return await stats_repo.get_analysis_progress()


@stats_router.get(
    "/api/stats/training",
    response_model=TrainingStats,
    summary="Get training statistics",
    description="Returns puzzle training statistics including attempts and accuracy.",
)
@cached(tag="training", ttl=300, version=1, key_params=[])
async def get_training_stats(
    request: Request,
    attempt_repo: PuzzleAttemptRepoDep,
) -> TrainingStats:
    stats = await attempt_repo.get_user_stats()

    return TrainingStats(**stats)


@stats_router.get(
    "/api/stats/training/html",
    response_class=HTMLResponse,
    summary="Get training statistics HTML",
    description="Returns training statistics as an HTML partial for HTMX.",
)
async def get_training_stats_html(
    request: Request,
    attempt_repo: PuzzleAttemptRepoDep,
) -> HTMLResponse:
    stats = await attempt_repo.get_user_stats()

    return request.app.state.templates.TemplateResponse(
        "_stats_partial.html",
        {"request": request, **stats},
    )


@stats_router.get(
    "/api/stats/activity-heatmap",
    response_model=ActivityHeatmapResponse,
    summary="Get puzzle activity heatmap data",
    description="Returns daily puzzle attempt counts for rendering a GitHub-style activity heatmap.",
)
@cached(tag="training", ttl=300, version=1, key_params=["days"])
async def get_activity_heatmap(
    request: Request,
    attempt_repo: PuzzleAttemptRepoDep,
    days: Annotated[
        int,
        Query(ge=30, le=365, description="Number of days to include"),
    ] = 365,
) -> dict[str, Any]:
    daily_counts = await attempt_repo.get_daily_attempt_counts(days)

    max_count = max((d["total"] for d in daily_counts.values()), default=0)
    total_attempts = sum(d["total"] for d in daily_counts.values())

    return {
        "daily_counts": daily_counts,
        "max_count": max_count,
        "total_days": len(daily_counts),
        "total_attempts": total_attempts,
    }


@stats_router.get(
    "/api/stats/blunders/by-phase",
    response_model=BlundersByPhase,
    summary="Get blunders by game phase",
    description="Returns blunder statistics grouped by game phase (opening, middlegame, endgame).",
)
@cached(tag="stats", ttl=300, version=1, key_params=["filters"])
async def get_blunders_by_phase(
    request: Request,
    stats_repo: StatsRepoDep,
    filters: StatsFilterDep,
) -> dict[str, Any]:
    return await stats_repo.get_blunders_by_phase_filtered(filters=filters)


@stats_router.get(
    "/api/stats/blunders/by-eco",
    response_model=BlundersByECO,
    summary="Get blunders by ECO opening code",
    description="Returns blunder statistics grouped by ECO opening code.",
)
@cached(tag="stats", ttl=300, version=1, key_params=["filters", "limit"])
async def get_blunders_by_eco(
    request: Request,
    stats_repo: StatsRepoDep,
    filters: StatsFilterDep,
    limit: Annotated[
        int,
        Query(ge=1, le=50, description="Maximum number of openings to return"),
    ] = 10,
) -> dict[str, Any]:
    return await stats_repo.get_blunders_by_eco(filters=filters, limit=limit)


@stats_router.get(
    "/api/stats/blunders/by-color",
    response_model=BlundersByColor,
    summary="Get blunders by player color",
    description="Returns blunder statistics grouped by the color the user was playing (white/black). Only counts the user's own blunders, not opponent blunders.",
)
@cached(tag="stats", ttl=300, version=1, key_params=["filters"])
async def get_blunders_by_color(
    request: Request,
    stats_repo: StatsRepoDep,
    filters: StatsFilterDep,
) -> dict[str, Any]:
    return await stats_repo.get_blunders_by_color(filters=filters)


class GamesByDateItem(BaseModel):
    date: str = Field(description="Date (YYYY-MM-DD)")
    game_count: int = Field(description="Number of games played on this date")
    avg_accuracy: float = Field(description="Average game accuracy (0-100)")


class GamesByDate(BaseModel):
    items: list[GamesByDateItem] = Field(description="Daily game statistics")


class GamesByHourItem(BaseModel):
    hour: int = Field(description="Hour of day (0-23)")
    game_count: int = Field(description="Number of games played during this hour")
    avg_accuracy: float = Field(description="Average game accuracy (0-100)")


class GamesByHour(BaseModel):
    items: list[GamesByHourItem] = Field(description="Hourly game statistics")


@stats_router.get(
    "/api/stats/games/by-date",
    response_model=GamesByDate,
    summary="Get game accuracy by date",
    description="Returns daily game counts and average accuracy for the user's moves.",
)
@cached(tag="stats", ttl=300, version=1, key_params=["filters"])
async def get_games_by_date(
    request: Request,
    stats_repo: StatsRepoDep,
    filters: StatsFilterDep,
) -> dict[str, Any]:
    items = await stats_repo.get_games_by_date(filters=filters)
    return {"items": items}


@stats_router.get(
    "/api/stats/games/by-hour",
    response_model=GamesByHour,
    summary="Get game accuracy by hour of day",
    description="Returns hourly game counts and average accuracy for the user's moves.",
)
@cached(tag="stats", ttl=300, version=1, key_params=["filters"])
async def get_games_by_hour(
    request: Request,
    stats_repo: StatsRepoDep,
    filters: StatsFilterDep,
) -> dict[str, Any]:
    items = await stats_repo.get_games_by_hour(filters=filters)
    return {"items": items}


class TacticalPatternItem(BaseModel):
    pattern: str = Field(description="Tactical pattern name (Fork, Pin, etc.)")
    pattern_id: int | None = Field(description="Tactical pattern ID")
    count: int = Field(description="Number of blunders with this pattern")
    percentage: float = Field(description="Percentage of total blunders")
    avg_cp_loss: float = Field(description="Average centipawn loss")


class BlundersByTacticalPattern(BaseModel):
    total_blunders: int = Field(description="Total number of blunders")
    by_pattern: list[TacticalPatternItem] = Field(
        description="Blunders grouped by tactical pattern"
    )


class GameTypeBlunderItem(BaseModel):
    game_type: str = Field(description="Game type (bullet, blitz, rapid, classical)")
    game_type_id: int = Field(description="Game type ID")
    count: int = Field(description="Number of blunders in this game type")
    percentage: float = Field(description="Percentage of total blunders")
    avg_cp_loss: float = Field(description="Average centipawn loss")


class BlundersByGameType(BaseModel):
    total_blunders: int = Field(description="Total number of blunders")
    by_game_type: list[GameTypeBlunderItem] = Field(
        description="Blunders grouped by game type"
    )


@stats_router.get(
    "/api/stats/blunders/by-tactical-pattern",
    response_model=BlundersByTacticalPattern,
    summary="Get blunders by tactical pattern",
    description="Returns blunder statistics grouped by tactical pattern (Fork, Pin, Skewer, etc.).",
)
@cached(tag="stats", ttl=300, version=1, key_params=["filters"])
async def get_blunders_by_tactical_pattern(
    request: Request,
    stats_repo: StatsRepoDep,
    filters: StatsFilterDep,
) -> dict[str, Any]:
    return await stats_repo.get_blunders_by_tactical_pattern(filters=filters)


@stats_router.get(
    "/api/stats/blunders/by-game-type",
    response_model=BlundersByGameType,
    summary="Get blunders by game type",
    description="Returns blunder statistics grouped by game type (bullet, blitz, rapid, classical).",
)
@cached(tag="stats", ttl=300, version=1, key_params=["filters"])
async def get_blunders_by_game_type(
    request: Request,
    stats_repo: StatsRepoDep,
    filters: StatsFilterDep,
) -> dict[str, Any]:
    return await stats_repo.get_blunders_by_game_type(filters=filters)


class CollapseDistributionItem(BaseModel):
    move_range: str = Field(
        description="Move range bucket (e.g., '1-5', '6-10', '41+')"
    )
    count: int = Field(description="Number of games with first blunder in this range")


class CollapsePointResponse(BaseModel):
    avg_collapse_move: int | None = Field(
        description="Average move number of first blunder"
    )
    median_collapse_move: int | None = Field(
        description="Median move number of first blunder"
    )
    distribution: list[CollapseDistributionItem] = Field(
        description="Distribution of first blunder by move-number buckets"
    )
    total_games_with_blunders: int = Field(
        description="Games where the user made at least one blunder"
    )
    total_games_without_blunders: int = Field(
        description="Games with zero blunders (clean games)"
    )


class ConversionResilienceResponse(BaseModel):
    conversion_rate: float = Field(
        description="Percentage of winning positions converted to wins"
    )
    resilience_rate: float = Field(
        description="Percentage of losing positions saved (draw or win)"
    )
    games_with_advantage: int = Field(
        description="Games where user had a winning position"
    )
    games_converted: int = Field(description="Games where the advantage was converted")
    games_with_disadvantage: int = Field(
        description="Games where user had a losing position"
    )
    games_saved: int = Field(description="Games where a losing position was saved")


class DifficultyBlunderItem(BaseModel):
    difficulty: str = Field(
        description="Difficulty bucket (easy, medium, hard, unscored)"
    )
    count: int = Field(description="Number of blunders in this bucket")
    percentage: float = Field(description="Percentage of total blunders")
    avg_cp_loss: float = Field(description="Average centipawn loss")


class BlundersByDifficulty(BaseModel):
    total_blunders: int = Field(description="Total number of blunders")
    by_difficulty: list[DifficultyBlunderItem] = Field(
        description="Blunders grouped by difficulty"
    )


@stats_router.get(
    "/api/stats/blunders/by-difficulty",
    response_model=BlundersByDifficulty,
    summary="Get blunders by difficulty",
    description="Returns blunder statistics grouped by difficulty bucket (easy, medium, hard).",
)
@cached(tag="stats", ttl=300, version=1, key_params=["filters"])
async def get_blunders_by_difficulty(
    request: Request,
    stats_repo: StatsRepoDep,
    filters: StatsFilterDep,
) -> dict[str, Any]:
    return await stats_repo.get_blunders_by_difficulty(filters=filters)


@stats_router.get(
    "/api/stats/collapse-point",
    response_model=CollapsePointResponse,
    summary="Get collapse point statistics",
    description="Returns the typical move number where the user makes their first blunder in a game.",
)
@cached(tag="stats", ttl=300, version=1, key_params=["filters"])
async def get_collapse_point(
    request: Request,
    stats_repo: StatsRepoDep,
    filters: StatsFilterDep,
) -> dict[str, Any]:
    return await stats_repo.get_collapse_point(filters=filters)


@stats_router.get(
    "/api/stats/conversion-resilience",
    response_model=ConversionResilienceResponse,
    summary="Get conversion and resilience rates",
    description="Returns how well the user converts winning positions and saves losing positions.",
)
@cached(tag="stats", ttl=300, version=1, key_params=["filters"])
async def get_conversion_resilience(
    request: Request,
    stats_repo: StatsRepoDep,
    filters: StatsFilterDep,
) -> dict[str, Any]:
    return await stats_repo.get_conversion_resilience(filters=filters)


@stats_router.get(
    "/api/stats/growth",
    response_model=GrowthMetricsResponse,
    summary="Get growth metrics",
    description="Returns rolling-window growth metrics showing how blunder frequency, severity, and move quality evolve over time.",
)
@cached(tag="stats", ttl=300, version=1, key_params=["filters", "window_size"])
async def get_growth_metrics(
    request: Request,
    stats_repo: StatsRepoDep,
    filters: StatsFilterDep,
    window_size: Annotated[
        int,
        Query(ge=5, le=100, description="Number of games per window"),
    ] = 20,
) -> GrowthMetricsResponse:
    per_game = await stats_repo.get_growth_metrics(filters=filters)
    windows = _compute_growth_windows(per_game, window_size)
    trend = _compute_trend(windows)
    return GrowthMetricsResponse(
        windows=windows,
        trend=trend,
        total_games=len(per_game),
        window_size=window_size,
    )
