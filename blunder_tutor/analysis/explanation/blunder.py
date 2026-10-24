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


def _is_ignored_threat(
    board: chess.Board,
    board_after: chess.Board,
    sq: chess.Square,
    piece: chess.Piece,
    blunder_move: chess.Move,
    player_color: chess.Color,
    enemy: chess.Color,
) -> bool:
    piece_val = piece_value(piece.piece_type)
    if piece_val < 3 or blunder_move.from_square == sq:
        return False
    if not is_under_profitable_attack(board, sq, piece_val, enemy):
        return False
    if board.is_capture(blunder_move) and blunder_move.to_square in board.attackers(
        enemy, sq
    ):
        return False
    piece_after = board_after.piece_at(sq)
    if piece_after is None or piece_after.color != player_color:
        return False
    return board_after.is_attacked_by(enemy, sq)


def _find_ignored_threat(
    board: chess.Board,
    blunder_move: chess.Move,
    player_color: chess.Color,
) -> tuple[chess.PieceType, chess.Square] | None:
    board_after = board.copy()
    board_after.push(blunder_move)
    enemy = not player_color
    candidates: list[tuple[int, chess.PieceType, chess.Square]] = []
    for sq in chess.SQUARES:
        piece = board.piece_at(sq)
        if piece is None or piece.color != player_color:
            continue
        if _is_ignored_threat(
            board, board_after, sq, piece, blunder_move, player_color, enemy
        ):
            candidates.append((piece_value(piece.piece_type), piece.piece_type, sq))
    if not candidates:
        return None
    _, piece_type, found_sq = max(candidates, key=lambda c: c[0])
    return (piece_type, found_sq)


def _blunder_missed_mate(
    board: chess.Board, best_move: chess.Move | None, **_: object
) -> I18nMessage | None:
    if best_move and move_gives_mate(board, best_move):
        return I18nMessage(key="explanation.blunder.missed_mate")
    return None


def _blunder_hanging(
    board: chess.Board,
    blunder_move: chess.Move,
    board_after: chess.Board,
    player_color: chess.Color,
    moved_key_nom: str,
    **_: object,
) -> I18nMessage | None:
    if not is_capturable(board_after, blunder_move.to_square, player_color):
        return None
    return I18nMessage(
        key="explanation.blunder.hanging_piece",
        params={
            "piece": moved_key_nom,
            "square": chess.square_name(blunder_move.to_square),
        },
    )


def _is_newly_exposed(
    board_before_null: chess.Board,
    board_after: chess.Board,
    sq: chess.Square,
    blunder_move_to: chess.Square,
    player_color: chess.Color,
) -> bool:
    piece = board_after.piece_at(sq)
    if piece is None or piece.color != player_color or sq == blunder_move_to:
        return False
    return is_capturable(board_after, sq, player_color) and not is_capturable(
        board_before_null, sq, player_color
    )


def _find_exposed_piece(
    board: chess.Board,
    board_after: chess.Board,
    blunder_move: chess.Move,
    player_color: chess.Color,
) -> tuple[chess.PieceType, chess.Square] | None:
    # Legal captures on both sides, with the opponent to move before the blunder too:
    # unpinning an attacker newly exposes a piece.
    board_before_null = board.copy()
    board_before_null.push(chess.Move.null())
    for sq in chess.SQUARES:
        if not _is_newly_exposed(
            board_before_null, board_after, sq, blunder_move.to_square, player_color
        ):
            continue
        piece = board_after.piece_at(sq)
        assert piece is not None
        return (piece.piece_type, sq)
    return None


def _blunder_exposed(
    board: chess.Board,
    board_after: chess.Board,
    blunder_move: chess.Move,
    player_color: chess.Color,
    moved_key_inst: str | None,
    **_: object,
) -> I18nMessage | None:
    if moved_key_inst is None:
        return None
    exposed = _find_exposed_piece(board, board_after, blunder_move, player_color)
    if exposed is None:
        return None
    piece_type, sq = exposed
    return I18nMessage(
        key="explanation.blunder.exposed_piece",
        params={
            "piece": moved_key_inst,
            "exposed": type_key(piece_type, "acc"),
            "square": chess.square_name(sq),
        },
    )


def _blunder_ignored_threat(
    board: chess.Board,
    blunder_move: chess.Move,
    player_color: chess.Color,
    **_: object,
) -> I18nMessage | None:
    ignored = _find_ignored_threat(board, blunder_move, player_color)
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


def _blunder_bad_capture(
    board: chess.Board,
    blunder_move: chess.Move,
    board_after: chess.Board,
    player_color: chess.Color,
    moved_key_inst: str | None,
    **_: object,
) -> I18nMessage | None:
    if moved_key_inst is None or not board.is_capture(blunder_move):
        return None
    captured = board.piece_at(blunder_move.to_square)
    mover = board.piece_at(blunder_move.from_square)
    if not (captured and mover):
        return None
    if piece_value(mover.piece_type) <= piece_value(captured.piece_type):
        return None
    if not has_legal_capture(board_after, blunder_move.to_square):
        return None
    return I18nMessage(
        key="explanation.blunder.bad_capture",
        params={"piece": moved_key_inst},
    )


def _blunder_cp_loss(cp_loss: int, **_: object) -> I18nMessage | None:
    pawn_loss = cp_loss / CENTIPAWNS_PER_PAWN
    if pawn_loss < 1:
        return None
    return I18nMessage(
        key="explanation.blunder.cp_loss",
        params={"loss": f"{pawn_loss:.1f}"},
    )


def _refutation_pv(
    board_after: chess.Board, refutation_line: list[str] | None
) -> PVAnalysis | None:
    if not refutation_line:
        return None
    try:
        reply = board_after.parse_san(refutation_line[0])
    except ValueError:
        return None
    return analyze_pv(board_after, reply, refutation_line)


def _blunder_refuted(
    board_after: chess.Board, refutation_line: list[str] | None, **_: object
) -> I18nMessage | None:
    pv = _refutation_pv(board_after, refutation_line)
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


_BLUNDER_STRATEGIES: tuple[Callable[..., I18nMessage | None], ...] = (
    _blunder_missed_mate,
    _blunder_hanging,
    _blunder_exposed,
    _blunder_ignored_threat,
    _blunder_bad_capture,
    _blunder_refuted,
    _blunder_cp_loss,
)


def explain_blunder(
    board: chess.Board,
    blunder_move: chess.Move,
    player_color: chess.Color,
    cp_loss: int,
    best_move: chess.Move | None = None,
    refutation_line: list[str] | None = None,
) -> I18nMessage | None:
    moved_key_nom = piece_key(board, blunder_move.from_square)
    if not moved_key_nom:
        return None
    board_after = board.copy()
    board_after.push(blunder_move)
    ctx = {
        "board": board,
        "blunder_move": blunder_move,
        "board_after": board_after,
        "player_color": player_color,
        "cp_loss": cp_loss,
        "best_move": best_move,
        "refutation_line": refutation_line,
        "moved_key_nom": moved_key_nom,
        "moved_key_inst": piece_key(board, blunder_move.from_square, "inst"),
    }
    for strategy in _BLUNDER_STRATEGIES:
        message = strategy(**ctx)
        if message is not None:
            return message
    return None
