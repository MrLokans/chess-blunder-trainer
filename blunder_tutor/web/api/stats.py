from __future__ import annotations

from datetime import date
from typing import Annotated, Any

from fastapi import HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.routing import APIRouter
from pydantic import BaseModel, Field

from blunder_tutor.web.api.schemas import ErrorResponse
from blunder_tutor.web.dependencies import (
    PuzzleAttemptRepoDep,
    SettingsRepoDep,
    StatsRepoDep,
)


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


stats_router = APIRouter()


@stats_router.get(
    "/api/stats",
    response_model=DashboardStats,
    summary="Get dashboard statistics",
    description="Returns overall dashboard statistics including total games, analyzed games, blunders, and pending analysis.",
)
async def get_dashboard_stats(stats_repo: StatsRepoDep) -> dict[str, Any]:
    return await stats_repo.get_overview_stats()


@stats_router.get(
    "/api/stats/games",
    response_model=GameBreakdown,
    summary="Get game breakdown",
    description="Returns game statistics grouped by source and/or username with optional filtering.",
)
async def get_game_breakdown(
    stats_repo: StatsRepoDep,
    source: Annotated[
        str | None,
        Query(description="Filter by game source (e.g., 'lichess', 'chesscom')"),
    ] = None,
    username: Annotated[
        str | None,
        Query(max_length=100, description="Filter by username"),
    ] = None,
) -> dict[str, Any]:
    breakdown = await stats_repo.get_game_breakdown(source=source, username=username)
    return {"items": breakdown}


@stats_router.get(
    "/api/stats/blunders",
    response_model=BlunderBreakdown,
    summary="Get blunder breakdown",
    description="Returns blunder statistics with optional filtering by username and date range.",
)
async def get_blunder_breakdown(
    stats_repo: StatsRepoDep,
    username: Annotated[
        str | None,
        Query(max_length=100, description="Filter by username"),
    ] = None,
    start_date: Annotated[
        date | None,
        Query(description="Start date for filtering (YYYY-MM-DD)"),
    ] = None,
    end_date: Annotated[
        date | None,
        Query(description="End date for filtering (YYYY-MM-DD)"),
    ] = None,
) -> dict[str, Any]:
    start_date_str = start_date.isoformat() if start_date else None
    end_date_str = end_date.isoformat() if end_date else None

    return await stats_repo.get_blunder_breakdown(
        username=username,
        start_date=start_date_str,
        end_date=end_date_str,
    )


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
    responses={400: {"model": ErrorResponse, "description": "No username configured"}},
    summary="Get training statistics",
    description="Returns puzzle training statistics for the configured user including attempts and accuracy.",
)
async def get_training_stats(
    settings_repo: SettingsRepoDep,
    attempt_repo: PuzzleAttemptRepoDep,
) -> TrainingStats:
    usernames = await settings_repo.get_configured_usernames()
    if not usernames:
        raise HTTPException(status_code=400, detail="No username configured")

    username = "multi" if len(usernames) > 1 else next(iter(usernames.values()))

    stats = await attempt_repo.get_user_stats(username)

    return TrainingStats(**stats)


@stats_router.get(
    "/api/stats/training/html",
    response_class=HTMLResponse,
    summary="Get training statistics HTML",
    description="Returns training statistics as an HTML partial for HTMX.",
)
async def get_training_stats_html(
    request: Request,
    settings_repo: SettingsRepoDep,
    attempt_repo: PuzzleAttemptRepoDep,
) -> HTMLResponse:
    usernames = await settings_repo.get_configured_usernames()
    if not usernames:
        stats = {
            "total_attempts": 0,
            "correct_attempts": 0,
            "incorrect_attempts": 0,
            "unique_puzzles": 0,
            "accuracy": 0.0,
        }
    else:
        username = "multi" if len(usernames) > 1 else next(iter(usernames.values()))
        stats = await attempt_repo.get_user_stats(username)

    return request.app.state.templates.TemplateResponse(
        "_stats_partial.html",
        {"request": request, **stats},
    )


@stats_router.get(
    "/api/stats/blunders/by-phase",
    response_model=BlundersByPhase,
    summary="Get blunders by game phase",
    description="Returns blunder statistics grouped by game phase (opening, middlegame, endgame).",
)
async def get_blunders_by_phase(
    stats_repo: StatsRepoDep,
    username: Annotated[
        str | None,
        Query(max_length=100, description="Filter by username"),
    ] = None,
    start_date: Annotated[
        date | None,
        Query(description="Start date for filtering (YYYY-MM-DD)"),
    ] = None,
    end_date: Annotated[
        date | None,
        Query(description="End date for filtering (YYYY-MM-DD)"),
    ] = None,
) -> dict[str, Any]:
    start_date_str = start_date.isoformat() if start_date else None
    end_date_str = end_date.isoformat() if end_date else None

    return await stats_repo.get_blunders_by_phase(
        username=username,
        start_date=start_date_str,
        end_date=end_date_str,
    )


@stats_router.get(
    "/api/stats/blunders/by-eco",
    response_model=BlundersByECO,
    summary="Get blunders by ECO opening code",
    description="Returns blunder statistics grouped by ECO opening code.",
)
async def get_blunders_by_eco(
    stats_repo: StatsRepoDep,
    username: Annotated[
        str | None,
        Query(max_length=100, description="Filter by username"),
    ] = None,
    start_date: Annotated[
        date | None,
        Query(description="Start date for filtering (YYYY-MM-DD)"),
    ] = None,
    end_date: Annotated[
        date | None,
        Query(description="End date for filtering (YYYY-MM-DD)"),
    ] = None,
    limit: Annotated[
        int,
        Query(ge=1, le=50, description="Maximum number of openings to return"),
    ] = 10,
) -> dict[str, Any]:
    start_date_str = start_date.isoformat() if start_date else None
    end_date_str = end_date.isoformat() if end_date else None

    return await stats_repo.get_blunders_by_eco(
        username=username,
        start_date=start_date_str,
        end_date=end_date_str,
        limit=limit,
    )


@stats_router.get(
    "/api/stats/blunders/by-color",
    response_model=BlundersByColor,
    summary="Get blunders by player color",
    description="Returns blunder statistics grouped by the color the user was playing (white/black). Only counts the user's own blunders, not opponent blunders.",
)
async def get_blunders_by_color(
    stats_repo: StatsRepoDep,
    username: Annotated[
        str | None,
        Query(max_length=100, description="Filter by username (required)"),
    ] = None,
    start_date: Annotated[
        date | None,
        Query(description="Start date for filtering (YYYY-MM-DD)"),
    ] = None,
    end_date: Annotated[
        date | None,
        Query(description="End date for filtering (YYYY-MM-DD)"),
    ] = None,
) -> dict[str, Any]:
    start_date_str = start_date.isoformat() if start_date else None
    end_date_str = end_date.isoformat() if end_date else None

    return await stats_repo.get_blunders_by_color(
        username=username,
        start_date=start_date_str,
        end_date=end_date_str,
    )
