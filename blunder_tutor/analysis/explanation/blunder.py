from __future__ import annotations

from collections.abc import Callable

import chess

from blunder_tutor.analysis.explanation.board import (
    CENTIPAWNS_PER_PAWN,
    has_legal_capture,
    is_capturable,
    is_under_profitable_attack,
    move_gives_mate,
    piece_value,
)
from blunder_tutor.analysis.explanation.lines import PVAnalysis, analyze_pv
from blunder_tutor.analysis.explanation.messages import I18nMessage, piece_key, type_key
from blunder_tutor.analysis.explanation.puzzle import Puzzle


def _moved_piece_key(puzzle: Puzzle, case: str = "") -> str:
    key = piece_key(puzzle.board, puzzle.blunder_move.from_square, case)
    assert key is not None
    return key


def _is_ignored_threat(puzzle: Puzzle, sq: chess.Square, piece: chess.Piece) -> bool:
    board, blunder_move = puzzle.board, puzzle.blunder_move
    enemy = not puzzle.player
    piece_val = piece_value(piece.piece_type)
    if piece_val < 3 or blunder_move.from_square == sq:
        return False
    if not is_under_profitable_attack(board, sq, piece_val, enemy):
        return False
    if board.is_capture(blunder_move) and blunder_move.to_square in board.attackers(
        enemy, sq
    ):
        return False
    piece_after = puzzle.board_after_blunder.piece_at(sq)
    if piece_after is None or piece_after.color != puzzle.player:
        return False
    return puzzle.board_after_blunder.is_attacked_by(enemy, sq)


def _find_ignored_threat(
    puzzle: Puzzle,
) -> tuple[chess.PieceType, chess.Square] | None:
    candidates = [
        (piece.piece_type, sq)
        for sq in chess.SQUARES
        if (piece := puzzle.board.piece_at(sq)) is not None
        and piece.color == puzzle.player
        and _is_ignored_threat(puzzle, sq, piece)
    ]
    return max(candidates, key=lambda found: piece_value(found[0]), default=None)


def _blunder_missed_mate(puzzle: Puzzle) -> I18nMessage | None:
    if puzzle.best_move and move_gives_mate(puzzle.board, puzzle.best_move):
        return I18nMessage(key="explanation.blunder.missed_mate")
    return None


def _blunder_hanging(puzzle: Puzzle) -> I18nMessage | None:
    landing = puzzle.blunder_move.to_square
    if not is_capturable(puzzle.board_after_blunder, landing, puzzle.player):
        return None
    return I18nMessage(
        key="explanation.blunder.hanging_piece",
        params={
            "piece": _moved_piece_key(puzzle),
            "square": chess.square_name(landing),
        },
    )


def _is_newly_exposed(
    puzzle: Puzzle, board_before_null: chess.Board, sq: chess.Square
) -> bool:
    piece = puzzle.board_after_blunder.piece_at(sq)
    if (
        piece is None
        or piece.color != puzzle.player
        or sq == puzzle.blunder_move.to_square
    ):
        return False
    return is_capturable(
        puzzle.board_after_blunder, sq, puzzle.player
    ) and not is_capturable(board_before_null, sq, puzzle.player)


def _find_exposed_piece(
    puzzle: Puzzle,
) -> tuple[chess.PieceType, chess.Square] | None:
    # Legal captures on both sides, with the opponent to move before the blunder too:
    # unpinning an attacker newly exposes a piece.
    board_before_null = puzzle.board.copy()
    board_before_null.push(chess.Move.null())
    exposed = [
        (piece.piece_type, sq)
        for sq in chess.SQUARES
        if _is_newly_exposed(puzzle, board_before_null, sq)
        and (piece := puzzle.board_after_blunder.piece_at(sq)) is not None
    ]
    return max(exposed, key=lambda found: piece_value(found[0]), default=None)


def _blunder_exposed(puzzle: Puzzle) -> I18nMessage | None:
    exposed = _find_exposed_piece(puzzle)
    if exposed is None:
        return None
    piece_type, sq = exposed
    return I18nMessage(
        key="explanation.blunder.exposed_piece",
        params={
            "piece": _moved_piece_key(puzzle, "inst"),
            "exposed": type_key(piece_type, "acc"),
            "square": chess.square_name(sq),
        },
    )


def _blunder_ignored_threat(puzzle: Puzzle) -> I18nMessage | None:
    ignored = _find_ignored_threat(puzzle)
    if ignored is None:
        return None
    piece_type, ignored_sq = ignored
    return I18nMessage(
        key="explanation.blunder.ignored_threat",
        params={
            "piece": type_key(piece_type, "acc"),
            "square": chess.square_name(ignored_sq),
        },
    )


def _blunder_bad_capture(puzzle: Puzzle) -> I18nMessage | None:
    board, blunder_move = puzzle.board, puzzle.blunder_move
    if not board.is_capture(blunder_move):
        return None
    captured = board.piece_at(blunder_move.to_square)
    mover = board.piece_at(blunder_move.from_square)
    if not (captured and mover):
        return None
    if piece_value(mover.piece_type) <= piece_value(captured.piece_type):
        return None
    if not has_legal_capture(puzzle.board_after_blunder, blunder_move.to_square):
        return None
    return I18nMessage(
        key="explanation.blunder.bad_capture",
        params={"piece": _moved_piece_key(puzzle, "inst")},
    )


def _blunder_cp_loss(puzzle: Puzzle) -> I18nMessage | None:
    pawn_loss = puzzle.cp_loss / CENTIPAWNS_PER_PAWN
    if pawn_loss < 1:
        return None
    return I18nMessage(
        key="explanation.blunder.cp_loss",
        params={"loss": f"{pawn_loss:.1f}"},
    )


def _refutation_pv(puzzle: Puzzle) -> PVAnalysis | None:
    refutation_line = puzzle.refutation_line
    if not refutation_line:
        return None
    try:
        reply = puzzle.board_after_blunder.parse_san(refutation_line[0])
    except ValueError:
        return None
    return analyze_pv(puzzle.board_after_blunder, reply, refutation_line)


def _blunder_refuted(puzzle: Puzzle) -> I18nMessage | None:
    pv = _refutation_pv(puzzle)
    if pv is None:
        return None
    params = {"reply": pv.moves_san[0]}
    # Engine lines stop at mate, so an odd length means the opponent delivered it.
    if pv.gives_mate and len(pv.moves_san) % 2 == 1:
        return I18nMessage(key="explanation.blunder.refuted_mate", params=params)
    # Net balance, not the biggest capture: Nxe6 fxe6 Rxe6+ takes a bishop, nets a pawn.
    if pv.balance_gain >= 1:
        return I18nMessage(key="explanation.blunder.refuted_material", params=params)
    return None


# First match wins: the most specific reason the move was a blunder comes first.
_BLUNDER_STRATEGIES: tuple[Callable[[Puzzle], I18nMessage | None], ...] = (
    _blunder_missed_mate,
    _blunder_hanging,
    _blunder_exposed,
    _blunder_ignored_threat,
    _blunder_bad_capture,
    _blunder_refuted,
    _blunder_cp_loss,
)


def explain_blunder(puzzle: Puzzle) -> I18nMessage | None:
    if puzzle.board.piece_at(puzzle.blunder_move.from_square) is None:
        return None
    return next(
        (
            message
            for strategy in _BLUNDER_STRATEGIES
            if (message := strategy(puzzle)) is not None
        ),
        None,
    )
