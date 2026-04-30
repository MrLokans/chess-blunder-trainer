from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from functools import partial
from typing import TYPE_CHECKING, Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from blunder_tutor.analysis.tactics import PATTERN_LABELS
from blunder_tutor.constants import PHASE_FROM_STRING, PHASE_LABELS
from blunder_tutor.events.event_types import TrainingEvent
from blunder_tutor.trainer import BlunderFilter
from blunder_tutor.utils.chess_utils import format_eval
from blunder_tutor.utils.explanation import generate_explanation, resolve_explanation

if TYPE_CHECKING:
    from collections.abc import Callable

    from blunder_tutor.services.analysis_service import AnalysisService
    from blunder_tutor.services.puzzle_service import PuzzleWithAnalysis
from blunder_tutor.web.api import _analysis_schemas as schemas
from blunder_tutor.web.api.schemas import ErrorResponse
from blunder_tutor.web.dependencies import (
    AnalysisServiceDep,
    ConfigDep,
    EngineThrottleDep,
    EventBusDep,
    PuzzleAttemptRepoDep,
    PuzzleServiceDep,
    SettingsRepoDep,
)


@dataclass(frozen=True)
class _PuzzleFilters:
    start_date: str | None
    end_date: str | None
    game_phases: list[int] | None
    tactical_patterns: list[int] | None
    game_types: list[int] | None
    player_colors: list[int] | None
    difficulty_ranges: list[tuple[int, int]] | None


def _puzzle_filters(
    start_date: Annotated[
        date | None, Query(description="Start date for puzzle filtering (YYYY-MM-DD)")
    ] = None,
    end_date: Annotated[
        date | None, Query(description="End date for puzzle filtering (YYYY-MM-DD)")
    ] = None,
    game_phases: Annotated[
        list[schemas.GamePhaseEnum] | None,
        Query(description="Filter by game phases (opening, middlegame, endgame)"),
    ] = None,
    tactical_patterns: Annotated[
        list[schemas.TacticalPatternEnum] | None,
        Query(description="Filter by tactical patterns (fork, pin, skewer, etc.)"),
    ] = None,
    game_types: Annotated[
        list[schemas.GameTypeEnum] | None,
        Query(description="Filter by game types (bullet, blitz, rapid, classical)"),
    ] = None,
    colors: Annotated[
        list[schemas.ColorEnum] | None,
        Query(description="Filter by player color (white, black)"),
    ] = None,
    difficulties: Annotated[
        list[schemas.DifficultyEnum] | None,
        Query(description="Filter by difficulty (easy, medium, hard)"),
    ] = None,
) -> _PuzzleFilters:
    return _PuzzleFilters(
        start_date=start_date.isoformat() if start_date else None,
        end_date=end_date.isoformat() if end_date else None,
        game_phases=(
            [PHASE_FROM_STRING[p.value] for p in game_phases] if game_phases else None
        ),
        tactical_patterns=(
            [schemas.PATTERN_FROM_STRING[p.value] for p in tactical_patterns]
            if tactical_patterns
            else None
        ),
        game_types=(
            [schemas.GAME_TYPE_FROM_STRING[g.value] for g in game_types]
            if game_types
            else None
        ),
        player_colors=(
            [schemas.COLOR_FROM_STRING[c.value] for c in colors] if colors else None
        ),
        difficulty_ranges=(
            [schemas.DIFFICULTY_RANGES[d.value] for d in difficulties]
            if difficulties
            else None
        ),
    )


PuzzleFiltersDep = Annotated[_PuzzleFilters, Depends(_puzzle_filters)]


def _build_blunder_filter(
    filters: _PuzzleFilters, spaced_repetition_days: int
) -> BlunderFilter:
    return BlunderFilter(
        start_date=filters.start_date,
        end_date=filters.end_date,
        exclude_recently_solved=True,
        spaced_repetition_days=spaced_repetition_days,
        game_phases=filters.game_phases,
        tactical_patterns=filters.tactical_patterns,
        game_types=filters.game_types,
        player_colors=filters.player_colors,
        difficulty_ranges=filters.difficulty_ranges,
    )


def _resolve_translator(request: Request) -> Callable[..., str]:
    i18n = getattr(request.app.state, "i18n", None)
    if i18n is None:
        return lambda key, **kw: key
    return partial(i18n.t, getattr(request.state, "locale", "en"))


def _build_puzzle_response(
    puzzle_with_analysis: PuzzleWithAnalysis, request: Request
) -> dict[str, Any]:
    puzzle_data = puzzle_with_analysis.puzzle
    analysis = puzzle_with_analysis.analysis

    pattern_label = (
        PATTERN_LABELS.get(puzzle_data.tactical_pattern)
        if puzzle_data.tactical_pattern is not None
        else None
    )
    explanation_raw = generate_explanation(
        fen=puzzle_data.fen,
        blunder_uci=puzzle_data.blunder_uci,
        best_move_uci=analysis.best_move_uci,
        tactical_pattern=pattern_label,
        cp_loss=puzzle_data.cp_loss,
        best_line=analysis.best_line,
    )
    explanation = resolve_explanation(explanation_raw, _resolve_translator(request))
    phase_label = (
        PHASE_LABELS.get(puzzle_data.game_phase)
        if puzzle_data.game_phase is not None
        else None
    )

    return {
        "game_id": puzzle_data.game_id,
        "ply": puzzle_data.ply,
        "blunder_uci": puzzle_data.blunder_uci,
        "blunder_san": puzzle_data.blunder_san,
        "fen": puzzle_data.fen,
        "player_color": puzzle_data.player_color,
        "eval_before": puzzle_data.eval_before,
        "eval_after": puzzle_data.eval_after,
        "cp_loss": puzzle_data.cp_loss,
        "eval_before_display": format_eval(
            puzzle_data.eval_before, puzzle_data.player_color
        ),
        "eval_after_display": format_eval(
            puzzle_data.eval_after, puzzle_data.player_color
        ),
        "best_move_uci": analysis.best_move_uci or "",
        "best_move_san": analysis.best_move_san or "",
        "best_line": analysis.best_line or [],
        "best_move_eval": puzzle_data.best_move_eval,
        "game_phase": phase_label,
        "tactical_pattern": pattern_label,
        "tactical_reason": puzzle_data.tactical_reason,
        "tactical_squares": puzzle_data.tactical_squares,
        "game_url": puzzle_data.game_url,
        "explanation_blunder": explanation.blunder_text or None,
        "explanation_best": explanation.best_move_text or None,
        "pre_move_uci": puzzle_data.pre_move_uci,
        "pre_move_fen": puzzle_data.pre_move_fen,
    }


async def _resolve_user_eval_cp(
    payload: schemas.SubmitMoveRequest,
    is_best: bool,
    is_blunder: bool,
    analysis_service: AnalysisService,
) -> int:
    if is_blunder:
        return payload.eval_after
    if is_best and payload.best_move_eval is not None:
        return payload.best_move_eval
    try:
        user_eval = await analysis_service.evaluate_move(
            payload.fen, payload.move, payload.player_color
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    return user_eval.eval_cp


analysis_router = APIRouter()


@analysis_router.get(
    "/api/puzzle",
    response_model=schemas.PuzzleResponse,
    responses={400: {"model": ErrorResponse, "description": "No puzzles available"}},
    summary="Get a puzzle",
    description="Returns a random blunder puzzle for the user to solve, with optional filtering.",
)
async def puzzle(
    request: Request,
    settings_repo: SettingsRepoDep,
    puzzle_service: PuzzleServiceDep,
    _throttle: EngineThrottleDep,
    filters: PuzzleFiltersDep,
) -> dict[str, Any]:
    spaced_repetition_days_str = await settings_repo.read_setting(
        "spaced_repetition_days"
    )
    spaced_repetition_days = (
        int(spaced_repetition_days_str)
        if spaced_repetition_days_str
        else schemas.SPACED_REPETITION_DAYS_DEFAULT
    )

    try:
        puzzle_with_analysis = await puzzle_service.get_puzzle_with_analysis(
            _build_blunder_filter(filters, spaced_repetition_days)
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc

    return _build_puzzle_response(puzzle_with_analysis, request)


@analysis_router.get(
    "/api/puzzle/specific",
    response_model=schemas.PuzzleResponse,
    responses={400: {"model": ErrorResponse, "description": "Puzzle not found"}},
    summary="Get a specific puzzle",
    description="Returns a specific blunder puzzle by game_id and ply.",
)
async def specific_puzzle(
    request: Request,
    puzzle_service: PuzzleServiceDep,
    _throttle: EngineThrottleDep,
    game_id: Annotated[str, Query(description="Game ID")],
    ply: Annotated[int, Query(description="Ply number")],
) -> dict[str, Any]:
    try:
        puzzle_with_analysis = await puzzle_service.get_specific_puzzle(game_id, ply)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc

    return _build_puzzle_response(puzzle_with_analysis, request)


@analysis_router.post(
    "/api/submit",
    response_model=schemas.SubmitMoveResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid move or no puzzle"}
    },
    summary="Submit puzzle move",
    description="Submit a move attempt for the current puzzle and receive evaluation feedback.",
)
async def submit(
    request: Request,
    payload: schemas.SubmitMoveRequest,
    attempt_repo: PuzzleAttemptRepoDep,
    analysis_service: AnalysisServiceDep,
    event_bus: EventBusDep,
    config: ConfigDep,
    _throttle: EngineThrottleDep,
) -> dict[str, Any]:
    try:
        user_san = analysis_service.get_move_san(payload.fen, payload.move)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid move"
        ) from None

    is_best = bool(payload.best_move_uci and payload.move == payload.best_move_uci)
    is_blunder = payload.move == payload.blunder_uci
    user_eval_cp = await _resolve_user_eval_cp(
        payload, is_best, is_blunder, analysis_service
    )

    await attempt_repo.record_attempt(
        game_id=payload.game_id,
        ply=payload.ply,
        was_correct=is_best,
        user_move_uci=payload.move,
        best_move_uci=payload.best_move_uci,
    )

    training_event = TrainingEvent.create_training_updated(
        user_key=config.username or "default"
    )
    await event_bus.publish(training_event)

    return {
        "user_san": user_san,
        "user_uci": payload.move,
        "user_eval": user_eval_cp,
        "user_eval_display": format_eval(user_eval_cp, payload.player_color),
        "best_san": payload.best_move_san,
        "best_uci": payload.best_move_uci,
        "best_line": payload.best_line,
        "is_best": is_best,
        "is_blunder": is_blunder,
        "blunder_san": payload.blunder_san,
    }


@analysis_router.post(
    "/api/analyze",
    response_model=schemas.AnalyzeMoveResponse,
    responses={400: {"model": ErrorResponse, "description": "Invalid FEN"}},
    summary="Analyze position",
    description="Analyze a specific chess position and return evaluation with best move.",
)
async def analyze_move(
    payload: schemas.AnalyzeMoveRequest,
    analysis_service: AnalysisServiceDep,
    _throttle: EngineThrottleDep,
) -> dict[str, Any]:
    try:
        analysis = await analysis_service.analyze_position(payload.fen)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid FEN"
        ) from None

    return {
        "eval": analysis.eval_cp,
        "eval_display": analysis.eval_display,
        "best_move_uci": analysis.best_move_uci,
        "best_move_san": analysis.best_move_san,
        "best_line": analysis.best_line,
    }
