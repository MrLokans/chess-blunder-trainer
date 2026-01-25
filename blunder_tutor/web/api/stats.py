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


# Response schemas
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


stats_router = APIRouter()


@stats_router.get(
    "/api/stats",
    response_model=DashboardStats,
    summary="Get dashboard statistics",
    description="Returns overall dashboard statistics including total games, analyzed games, blunders, and pending analysis.",
)
def get_dashboard_stats(stats_repo: StatsRepoDep) -> dict[str, Any]:
    return stats_repo.get_overview_stats()


@stats_router.get(
    "/api/stats/games",
    response_model=GameBreakdown,
    summary="Get game breakdown",
    description="Returns game statistics grouped by source and/or username with optional filtering.",
)
def get_game_breakdown(
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
    breakdown = stats_repo.get_game_breakdown(source=source, username=username)
    return {"items": breakdown}


@stats_router.get(
    "/api/stats/blunders",
    response_model=BlunderBreakdown,
    summary="Get blunder breakdown",
    description="Returns blunder statistics with optional filtering by username and date range.",
)
def get_blunder_breakdown(
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

    return stats_repo.get_blunder_breakdown(
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
def get_analysis_progress(stats_repo: StatsRepoDep) -> dict[str, Any]:
    return stats_repo.get_analysis_progress()


@stats_router.get(
    "/api/stats/training",
    response_model=TrainingStats,
    responses={400: {"model": ErrorResponse, "description": "No username configured"}},
    summary="Get training statistics",
    description="Returns puzzle training statistics for the configured user including attempts and accuracy.",
)
def get_training_stats(
    settings_repo: SettingsRepoDep,
    attempt_repo: PuzzleAttemptRepoDep,
) -> TrainingStats:
    usernames = settings_repo.get_configured_usernames()
    if not usernames:
        raise HTTPException(status_code=400, detail="No username configured")

    # Use "multi" if multiple usernames (matching trainer.py logic)
    username = "multi" if len(usernames) > 1 else next(iter(usernames.values()))

    stats = attempt_repo.get_user_stats(username)

    return TrainingStats(**stats)


@stats_router.get(
    "/api/stats/training/html",
    response_class=HTMLResponse,
    summary="Get training statistics HTML",
    description="Returns training statistics as an HTML partial for HTMX.",
)
def get_training_stats_html(
    request: Request,
    settings_repo: SettingsRepoDep,
    attempt_repo: PuzzleAttemptRepoDep,
) -> HTMLResponse:
    usernames = settings_repo.get_configured_usernames()
    if not usernames:
        stats = {
            "total_attempts": 0,
            "correct_attempts": 0,
            "incorrect_attempts": 0,
            "unique_puzzles": 0,
            "accuracy": 0.0,
        }
    else:
        # Use "multi" if multiple usernames (matching trainer.py logic)
        username = "multi" if len(usernames) > 1 else next(iter(usernames.values()))
        stats = attempt_repo.get_user_stats(username)

    return request.app.state.templates.TemplateResponse(
        "_stats_partial.html",
        {"request": request, **stats},
    )
