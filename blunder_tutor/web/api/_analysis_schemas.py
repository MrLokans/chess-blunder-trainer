from __future__ import annotations

from enum import StrEnum
from types import MappingProxyType

from pydantic import BaseModel, Field

from blunder_tutor.analysis.tactics import TacticalPattern


class GamePhaseEnum(StrEnum):
    opening = "opening"
    middlegame = "middlegame"
    endgame = "endgame"


class TacticalPatternEnum(StrEnum):
    fork = "fork"
    pin = "pin"
    skewer = "skewer"
    discovered_attack = "discovered_attack"
    discovered_check = "discovered_check"
    double_check = "double_check"
    back_rank = "back_rank"
    hanging_piece = "hanging_piece"
    none = "none"


class GameTypeEnum(StrEnum):
    ultrabullet = "ultrabullet"
    bullet = "bullet"
    blitz = "blitz"
    rapid = "rapid"
    classical = "classical"
    correspondence = "correspondence"


class ColorEnum(StrEnum):
    white = "white"
    black = "black"


class DifficultyEnum(StrEnum):
    easy = "easy"
    medium = "medium"
    hard = "hard"


# Default for spaced_repetition_days when not configured; mirrors the
# default used by the settings model (SettingsRequest.spaced_repetition_days).
SPACED_REPETITION_DAYS_DEFAULT = 30


DIFFICULTY_RANGES = MappingProxyType(
    {
        "easy": (0, 30),
        "medium": (31, 60),
        "hard": (61, 100),
    }
)


PATTERN_FROM_STRING = MappingProxyType(
    {
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
)

GAME_TYPE_FROM_STRING = MappingProxyType(
    {
        "ultrabullet": 0,
        "bullet": 1,
        "blitz": 2,
        "rapid": 3,
        "classical": 4,
        "correspondence": 5,
    }
)

COLOR_FROM_STRING = MappingProxyType(
    {
        "white": 0,
        "black": 1,
    }
)


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
    explanation_blunder: str | None = Field(
        default=None,
        description="Beginner-friendly explanation of why the move was a blunder",
    )
    explanation_best: str | None = Field(
        default=None,
        description="Beginner-friendly explanation of what the best move achieves",
    )
    pre_move_uci: str | None = Field(
        default=None,
        description="Opponent's preceding move in UCI notation (e.g., 'e7e5'), null for ply 1",
    )
    pre_move_fen: str | None = Field(
        default=None,
        description="Position FEN before the opponent's preceding move, null for ply 1",
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
