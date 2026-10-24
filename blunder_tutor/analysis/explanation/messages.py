from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

import chess

PIECE_NAMES = frozendict(
    {
        chess.PAWN: "pawn",
        chess.KNIGHT: "knight",
        chess.BISHOP: "bishop",
        chess.ROOK: "rook",
        chess.QUEEN: "queen",
        chess.KING: "king",
    }
)


PIECE_I18N_KEYS = {
    chess.PAWN: "chess.piece.pawn",
    chess.KNIGHT: "chess.piece.knight",
    chess.BISHOP: "chess.piece.bishop",
    chess.ROOK: "chess.piece.rook",
    chess.QUEEN: "chess.piece.queen",
    chess.KING: "chess.piece.king",
}


_PIECE_KEY_PREFIX = "chess.piece."


@dataclass(frozen=True)
class I18nMessage:
    key: str
    params: dict[str, str | float] = field(default_factory=dict)


@dataclass(frozen=True)
class BlunderExplanation:
    blunder: I18nMessage | None
    best_move: I18nMessage | None


@dataclass(frozen=True)
class ResolvedExplanation:
    blunder_text: str
    best_move_text: str


def _resolve_message(message: I18nMessage | None, t: Callable[..., str]) -> str:
    if message is None:
        return ""
    params = dict(message.params)
    for key, value in list(params.items()):
        if isinstance(value, str) and value.startswith(_PIECE_KEY_PREFIX):
            params[key] = t(value)
    return t(message.key, **params)


def resolve_explanation(
    explanation: BlunderExplanation,
    t: Callable[..., str],
) -> ResolvedExplanation:
    return ResolvedExplanation(
        blunder_text=_resolve_message(explanation.blunder, t),
        best_move_text=_resolve_message(explanation.best_move, t),
    )


def piece_key(board: chess.Board, square: chess.Square, case: str = "") -> str | None:
    piece = board.piece_at(square)
    if piece is None:
        return None
    base = PIECE_I18N_KEYS.get(piece.piece_type)
    if base is None:
        return None
    return f"{base}.{case}" if case else base


def type_key(piece_type: chess.PieceType, case: str = "") -> str:
    base = PIECE_I18N_KEYS.get(piece_type, "")
    return f"{base}.{case}" if case else base
