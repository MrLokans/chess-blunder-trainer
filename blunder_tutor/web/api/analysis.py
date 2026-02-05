from __future__ import annotations

from datetime import date
from enum import Enum
from typing import Annotated, Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from blunder_tutor.analysis.tactics import PATTERN_LABELS, TacticalPattern
from blunder_tutor.constants import PHASE_FROM_STRING, PHASE_LABELS
from blunder_tutor.web.api.schemas import ErrorResponse
from blunder_tutor.web.dependencies import (
    AnalysisServiceDep,
    ConfigDep,
    PuzzleAttemptRepoDep,
    PuzzleServiceDep,
    SettingsRepoDep,
)


class GamePhaseEnum(str, Enum):
    opening = "opening"
    middlegame = "middlegame"
    endgame = "endgame"


class TacticalPatternEnum(str, Enum):
    fork = "fork"
    pin = "pin"
    skewer = "skewer"
    discovered_attack = "discovered_attack"
    discovered_check = "discovered_check"
    double_check = "double_check"
    back_rank = "back_rank"
    hanging_piece = "hanging_piece"
    none = "none"


class GameTypeEnum(str, Enum):
    ultrabullet = "ultrabullet"
    bullet = "bullet"
    blitz = "blitz"
    rapid = "rapid"
    classical = "classical"
    correspondence = "correspondence"


class ColorEnum(str, Enum):
    white = "white"
    black = "black"


PATTERN_FROM_STRING = {
    "fork": TacticalPattern.FORK,
    "pin": TacticalPattern.PIN,
    "skewer": TacticalPattern.SKEWER,
    "discovered_attack": TacticalPattern.DISCOVERED_ATTACK,
    "discovered_check": TacticalPattern.DISCOVERED_CHECK,
    "double_check": TacticalPattern.DOUBLE_CHECK,
    "back_rank": TacticalPattern.BACK_RANK_THREAT,
    "hanging_piece": TacticalPattern.HANGING_PIECE,
    "none": TacticalPattern.NONE,
}

GAME_TYPE_FROM_STRING = {
    "ultrabullet": 0,
    "bullet": 1,
    "blitz": 2,
    "rapid": 3,
    "classical": 4,
    "correspondence": 5,
}

COLOR_FROM_STRING = {
    "white": 0,
    "black": 1,
}


class SubmitMoveRequest(BaseModel):
    move: str = Field(description="Move in UCI notation (e.g., 'e2e4')")
    fen: str = Field(description="Position FEN before the move")
    game_id: str = Field(description="Game ID of the puzzle")
    ply: int = Field(description="Ply of the puzzle")
    blunder_uci: str = Field(description="The blunder move in UCI notation")
    blunder_san: str = Field(description="The blunder move in SAN notation")
    best_move_uci: str | None = Field(description="Best move in UCI notation")
    best_move_san: str | None = Field(description="Best move in SAN notation")
    best_line: list[str] = Field(description="Best continuation line")
    player_color: str = Field(description="Player color ('white' or 'black')")
    username: str = Field(description="Username for the puzzle attempt")
    eval_after: int = Field(description="Evaluation after the blunder")
    best_move_eval: int | None = Field(description="Cached evaluation after best move")


class AnalyzeMoveRequest(BaseModel):
    fen: str = Field(description="FEN string of the position to analyze")


class PuzzleResponse(BaseModel):
    game_id: str = Field(description="Unique game identifier")
    ply: int = Field(description="Move number (half-move)")
    blunder_uci: str = Field(description="The blunder move in UCI notation")
    blunder_san: str = Field(description="The blunder move in SAN notation")
    fen: str = Field(description="Position FEN after the previous move")
    player_color: str = Field(description="Player color ('white' or 'black')")
    username: str = Field(description="Username for this puzzle")
    eval_before: int = Field(description="Evaluation in centipawns before the blunder")
    eval_after: int = Field(description="Evaluation in centipawns after the blunder")
    cp_loss: int = Field(description="Centipawn loss from the blunder")
    eval_before_display: str = Field(description="Formatted evaluation before blunder")
    eval_after_display: str = Field(description="Formatted evaluation after blunder")
    best_move_uci: str | None = Field(description="Best move in UCI notation")
    best_move_san: str | None = Field(description="Best move in SAN notation")
    best_line: list[str] = Field(description="Best continuation line (up to 5 moves)")
    best_move_eval: int | None = Field(description="Evaluation after best move")
    game_phase: str | None = Field(
        description="Game phase (opening, middlegame, endgame)"
    )
    tactical_pattern: str | None = Field(
        description="Tactical pattern involved (Fork, Pin, etc.)"
    )
    tactical_reason: str | None = Field(
        description="Human-readable explanation of why this was a blunder"
    )
    tactical_squares: list[str] | None = Field(
        description="Squares involved in the tactic for highlighting (e.g., ['f7', 'd8', 'h8'])"
    )
    game_url: str | None = Field(
        description="URL to the original game on Lichess or Chess.com"
    )


class SubmitMoveResponse(BaseModel):
    user_san: str = Field(description="User's move in SAN notation")
    user_uci: str = Field(description="User's move in UCI notation")
    user_eval: int = Field(description="Evaluation after user's move")
    user_eval_display: str = Field(description="Formatted evaluation after user's move")
    best_san: str | None = Field(description="Best move in SAN notation")
    best_uci: str | None = Field(description="Best move in UCI notation")
    best_line: list[str] = Field(description="Best continuation line")
    is_best: bool = Field(description="Whether user's move was the best move")
    is_blunder: bool = Field(description="Whether user repeated the original blunder")
    blunder_san: str = Field(description="Original blunder move in SAN notation")


class AnalyzeMoveResponse(BaseModel):
    eval: int = Field(description="Position evaluation in centipawns")
    eval_display: str = Field(description="Formatted evaluation display")
    best_move_uci: str | None = Field(description="Best move in UCI notation")
    best_move_san: str | None = Field(description="Best move in SAN notation")
    best_line: list[str] = Field(description="Best continuation line (up to 5 moves)")


analysis_router = APIRouter()


@analysis_router.get(
    "/api/puzzle",
    response_model=PuzzleResponse,
    responses={400: {"model": ErrorResponse, "description": "No username configured"}},
    summary="Get a puzzle",
    description="Returns a random blunder puzzle for the user to solve, with optional filtering.",
)
async def puzzle(
    config: ConfigDep,
    settings_repo: SettingsRepoDep,
    puzzle_service: PuzzleServiceDep,
    start_date: Annotated[
        date | None,
        Query(description="Start date for puzzle filtering (YYYY-MM-DD)"),
    ] = None,
    end_date: Annotated[
        date | None,
        Query(description="End date for puzzle filtering (YYYY-MM-DD)"),
    ] = None,
    game_phases: Annotated[
        list[GamePhaseEnum] | None,
        Query(description="Filter by game phases (opening, middlegame, endgame)"),
    ] = None,
    tactical_patterns: Annotated[
        list[TacticalPatternEnum] | None,
        Query(description="Filter by tactical patterns (fork, pin, skewer, etc.)"),
    ] = None,
    game_types: Annotated[
        list[GameTypeEnum] | None,
        Query(description="Filter by game types (bullet, blitz, rapid, classical)"),
    ] = None,
    colors: Annotated[
        list[ColorEnum] | None,
        Query(description="Filter by player color (white, black)"),
    ] = None,
) -> dict[str, Any]:
    username = config.username
    source = None

    if not username:
        usernames = await settings_repo.get_configured_usernames()

        if not usernames:
            raise HTTPException(
                status_code=400,
                detail="No username configured. Please configure your username in Settings.",
            )

        if len(usernames) > 1:
            username = list(usernames.values())
            source = None
        else:
            platform, uname = next(iter(usernames.items()))
            username = uname
            source = platform

    start_date_str = start_date.isoformat() if start_date else None
    end_date_str = end_date.isoformat() if end_date else None

    spaced_repetition_days_str = await settings_repo.get_setting(
        "spaced_repetition_days"
    )
    spaced_repetition_days = (
        int(spaced_repetition_days_str) if spaced_repetition_days_str else 30
    )

    game_phases_int = (
        [PHASE_FROM_STRING[p.value] for p in game_phases] if game_phases else None
    )

    tactical_patterns_int = (
        [PATTERN_FROM_STRING[p.value] for p in tactical_patterns]
        if tactical_patterns
        else None
    )

    game_types_int = (
        [GAME_TYPE_FROM_STRING[g.value] for g in game_types] if game_types else None
    )

    colors_int = [COLOR_FROM_STRING[c.value] for c in colors] if colors else None

    try:
        puzzle_with_analysis = await puzzle_service.get_puzzle_with_analysis(
            username=username,
            source=source,
            start_date=start_date_str,
            end_date=end_date_str,
            exclude_recently_solved=True,
            spaced_repetition_days=spaced_repetition_days,
            game_phases=game_phases_int,
            tactical_patterns=tactical_patterns_int,
            game_types=game_types_int,
            player_colors=colors_int,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    puzzle_data = puzzle_with_analysis.puzzle
    analysis = puzzle_with_analysis.analysis

    from blunder_tutor.utils.chess_utils import format_eval

    return {
        "game_id": puzzle_data.game_id,
        "ply": puzzle_data.ply,
        "blunder_uci": puzzle_data.blunder_uci,
        "blunder_san": puzzle_data.blunder_san,
        "fen": puzzle_data.fen,
        "player_color": puzzle_data.player_color,
        "username": puzzle_data.username,
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
        "game_phase": PHASE_LABELS.get(puzzle_data.game_phase)
        if puzzle_data.game_phase is not None
        else None,
        "tactical_pattern": PATTERN_LABELS.get(puzzle_data.tactical_pattern)
        if puzzle_data.tactical_pattern is not None
        else None,
        "tactical_reason": puzzle_data.tactical_reason,
        "tactical_squares": puzzle_data.tactical_squares,
        "game_url": puzzle_data.game_url,
    }


@analysis_router.post(
    "/api/submit",
    response_model=SubmitMoveResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid move or no puzzle"}
    },
    summary="Submit puzzle move",
    description="Submit a move attempt for the current puzzle and receive evaluation feedback.",
)
async def submit(
    payload: SubmitMoveRequest,
    attempt_repo: PuzzleAttemptRepoDep,
    analysis_service: AnalysisServiceDep,
) -> dict[str, Any]:
    try:
        user_san = analysis_service.get_move_san(payload.fen, payload.move)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid move") from None

    is_best = payload.best_move_uci and payload.move == payload.best_move_uci
    is_blunder = payload.move == payload.blunder_uci

    if is_blunder:
        user_eval_cp = payload.eval_after
    elif is_best and payload.best_move_eval is not None:
        user_eval_cp = payload.best_move_eval
    else:
        try:
            user_eval = await analysis_service.evaluate_move(
                payload.fen, payload.move, payload.player_color
            )
            user_eval_cp = user_eval.eval_cp
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    from blunder_tutor.utils.chess_utils import format_eval

    user_eval_display = format_eval(user_eval_cp, payload.player_color)

    await attempt_repo.record_attempt(
        game_id=payload.game_id,
        ply=payload.ply,
        username=payload.username,
        was_correct=is_best,
        user_move_uci=payload.move,
        best_move_uci=payload.best_move_uci,
    )

    return {
        "user_san": user_san,
        "user_uci": payload.move,
        "user_eval": user_eval_cp,
        "user_eval_display": user_eval_display,
        "best_san": payload.best_move_san,
        "best_uci": payload.best_move_uci,
        "best_line": payload.best_line,
        "is_best": is_best,
        "is_blunder": is_blunder,
        "blunder_san": payload.blunder_san,
    }


@analysis_router.post(
    "/api/analyze",
    response_model=AnalyzeMoveResponse,
    responses={400: {"model": ErrorResponse, "description": "Invalid FEN"}},
    summary="Analyze position",
    description="Analyze a specific chess position and return evaluation with best move.",
)
async def analyze_move(
    payload: AnalyzeMoveRequest, analysis_service: AnalysisServiceDep
) -> dict[str, Any]:
    try:
        analysis = await analysis_service.analyze_position(payload.fen)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid FEN") from None

    return {
        "eval": analysis.eval_cp,
        "eval_display": analysis.eval_display,
        "best_move_uci": analysis.best_move_uci,
        "best_move_san": analysis.best_move_san,
        "best_line": analysis.best_line,
    }
