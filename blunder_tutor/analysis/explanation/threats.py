from __future__ import annotations

from dataclasses import dataclass

import chess

from blunder_tutor.analysis.explanation.board import piece_value
from blunder_tutor.analysis.explanation.messages import type_key


def _find_new_attacks(
    board_before: chess.Board,
    board_after: chess.Board,
    attacker_color: chess.Color,
) -> list[tuple[chess.Square, chess.PieceType, int]]:
    enemy = not attacker_color
    results = []
    for sq in chess.SQUARES:
        piece = board_after.piece_at(sq)
        if piece and piece.color == enemy and piece.piece_type != chess.KING:
            was_attacked = board_before.is_attacked_by(attacker_color, sq)
            now_attacked = board_after.is_attacked_by(attacker_color, sq)
            if now_attacked and not was_attacked:
                results.append((sq, piece.piece_type, piece_value(piece.piece_type)))
    return results


THREAT_MATE = "threatens_mate"


THREAT_CAPTURE_CHECK = "threatens_capture_check"


THREAT_PIECE = "creates_threat"


THREAT_ATTACKS = "attacks_piece"


@dataclass(frozen=True)
class _Threat:
    kind: str
    piece_key: str = ""


def _threat_from_new_attacks(
    board: chess.Board, board_after: chess.Board, player: chess.Color
) -> _Threat | None:
    new_attacks = _find_new_attacks(board, board_after, player)
    if not new_attacks:
        return None
    new_attacks.sort(key=lambda x: x[2], reverse=True)
    best_target = new_attacks[0]
    if best_target[2] < 5:
        return None
    return _Threat(kind=THREAT_ATTACKS, piece_key=type_key(best_target[1], "acc"))


def _classify_null_move_threat(
    null_board: chess.Board,
    candidate_move: chess.Move,
    piece: chess.Piece,
    player: chess.Color,
) -> _Threat | None:
    board_check = null_board.copy()
    board_check.push(candidate_move)
    if board_check.is_checkmate():
        return _Threat(kind=THREAT_MATE)
    if not board_check.is_check():
        return None
    if null_board.is_capture(candidate_move):
        captured = null_board.piece_at(candidate_move.to_square)
        if captured and piece_value(captured.piece_type) >= 3:
            return _Threat(
                kind=THREAT_CAPTURE_CHECK,
                piece_key=type_key(captured.piece_type, "gen"),
            )
    if piece.piece_type != chess.PAWN:
        return _Threat(
            kind=THREAT_PIECE,
            piece_key=type_key(piece.piece_type, "gen"),
        )
    return None


def _threats_available(board: chess.Board, player: chess.Color) -> list[_Threat]:
    threats = []
    for candidate_move in board.legal_moves:
        piece = board.piece_at(candidate_move.from_square)
        if not piece or piece.color != player:
            continue
        threat = _classify_null_move_threat(board, candidate_move, piece, player)
        if threat is not None:
            threats.append(threat)
    return threats


def _threat_from_null_move(
    board: chess.Board, board_after: chess.Board, player: chess.Color
) -> _Threat | None:
    if board_after.is_check():
        return None
    null_board = board_after.copy()
    null_board.push(chess.Move.null())
    # Only threats the best move created: a rook check that was available all along
    # doesn't explain the move, even if the rook now gives it from another square.
    existing = set(_threats_available(board, player)) if not board.is_check() else set()
    return next(
        (t for t in _threats_available(null_board, player) if t not in existing), None
    )


def detect_next_move_threat(board: chess.Board, move: chess.Move) -> _Threat | None:
    board_after = board.copy()
    board_after.push(move)
    player = board.turn

    new_attack_threat = _threat_from_new_attacks(board, board_after, player)
    if new_attack_threat is not None:
        return new_attack_threat
    return _threat_from_null_move(board, board_after, player)
