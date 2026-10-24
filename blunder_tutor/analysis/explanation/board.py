from __future__ import annotations

import chess

CENTIPAWNS_PER_PAWN = 100


MINOR_PIECE_VALUE = 3


PIECE_VALUES = frozendict(
    {
        chess.PAWN: 1,
        chess.KNIGHT: 3,
        chess.BISHOP: 3,
        chess.ROOK: 5,
        chess.QUEEN: 9,
        chess.KING: 0,
    }
)


def is_hanging(board: chess.Board, square: chess.Square, color: chess.Color) -> bool:
    piece = board.piece_at(square)
    if piece is None or piece.color != color:
        return False
    enemy = not color
    return bool(board.is_attacked_by(enemy, square)) and not bool(
        board.attackers(color, square)
    )


def has_legal_capture(board: chess.Board, square: chess.Square) -> bool:
    return any(move.to_square == square for move in board.legal_moves)


def is_capturable(board: chess.Board, square: chess.Square, color: chess.Color) -> bool:
    """Hanging with the opponent to move and able to take it: an attacker that is
    pinned, or a check to answer first, doesn't count."""
    return is_hanging(board, square, color) and has_legal_capture(board, square)


def move_gives_check(board: chess.Board, move: chess.Move) -> bool:
    b = board.copy()
    b.push(move)
    return b.is_check()


def move_gives_mate(board: chess.Board, move: chess.Move) -> bool:
    b = board.copy()
    b.push(move)
    return b.is_checkmate()


def piece_value(piece_type: chess.PieceType) -> int:
    return PIECE_VALUES.get(piece_type, 0)


def _iter_hanging_enemies(board: chess.Board, enemy: chess.Color):
    for sq in chess.SQUARES:
        piece = board.piece_at(sq)
        if (
            piece
            and piece.color == enemy
            and piece.piece_type != chess.KING
            and is_hanging(board, sq, enemy)
        ):
            yield sq, piece


def find_hanging_piece(
    board: chess.Board,
    move: chess.Move,
    player_color: chess.Color,
) -> tuple[chess.PieceType, chess.Square] | None:
    board_after = board.copy()
    board_after.push(move)
    enemy = not player_color
    attacked_by_mover = board_after.attacks(move.to_square)
    candidates = [
        (piece_value(piece.piece_type), piece.piece_type, sq)
        for sq, piece in _iter_hanging_enemies(board_after, enemy)
        if sq in attacked_by_mover
    ]
    if not candidates:
        return None
    _, piece_type, sq = max(candidates, key=lambda c: c[0])
    return (piece_type, sq)


def _min_attacker_value(
    board: chess.Board,
    sq: chess.Square,
    attacker_color: chess.Color,
) -> int | None:
    attackers = board.attackers(attacker_color, sq)
    if not attackers:
        return None
    return min(
        piece_value(board.piece_at(a).piece_type)
        for a in attackers
        if board.piece_at(a)
    )


def is_under_profitable_attack(
    board: chess.Board,
    sq: chess.Square,
    piece_val: int,
    enemy: chess.Color,
) -> bool:
    min_attacker = _min_attacker_value(board, sq, enemy)
    return min_attacker is not None and min_attacker < piece_val


def _is_safe_destination(
    board_after: chess.Board,
    dest: chess.Square,
    enemy: chess.Color,
    piece_val: int,
) -> bool:
    for attacker_sq in board_after.attackers(enemy, dest):
        attacker = board_after.piece_at(attacker_sq)
        if attacker and piece_value(attacker.piece_type) < piece_val:
            return False
    return True


def _retreat_candidate(
    board: chess.Board, best_move: chess.Move
) -> tuple[chess.Piece, int, chess.Color] | None:
    if board.is_capture(best_move):
        return None
    player = board.turn
    piece = board.piece_at(best_move.from_square)
    if piece is None or piece.color != player or piece.piece_type == chess.KING:
        return None
    piece_val = piece_value(piece.piece_type)
    if piece_val < 3:
        return None
    enemy = not player
    if not is_under_profitable_attack(board, best_move.from_square, piece_val, enemy):
        return None
    return (piece, piece_val, enemy)


def is_retreat_to_safety(
    board: chess.Board,
    best_move: chess.Move,
) -> tuple[chess.PieceType, chess.Square] | None:
    candidate = _retreat_candidate(board, best_move)
    if candidate is None:
        return None
    piece, piece_val, enemy = candidate
    board_after = board.copy()
    board_after.push(best_move)
    if not _is_safe_destination(board_after, best_move.to_square, enemy, piece_val):
        return None
    return (piece.piece_type, best_move.from_square)


def _count_material(board: chess.Board, color: chess.Color) -> int:
    return sum(
        piece_value(piece.piece_type)
        for sq in chess.SQUARES
        if (piece := board.piece_at(sq)) and piece.color == color
    )


def material_balance(board: chess.Board, color: chess.Color) -> int:
    return _count_material(board, color) - _count_material(board, not color)
