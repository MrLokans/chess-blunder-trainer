from __future__ import annotations

import chess

from blunder_tutor.analysis.explanation.lines import final_capture_at_risk, line_boards
from blunder_tutor.analysis.explanation.messages import I18nMessage

_PAWN_DAMAGE_PRIORITY = ("king_shelter", "doubled")


_PAWN_DAMAGE_KEYS = frozendict(
    {
        "king_shelter": "explanation.best.opens_king",
        "doubled": "explanation.best.doubles_pawns",
    }
)


_KING_HOME_RANKS = frozendict({chess.WHITE: (0, 1), chess.BLACK: (7, 6)})


_CENTRE_FILES = (3, 4)


def _pawn_weaknesses(board: chess.Board, color: chess.Color) -> set[tuple[str, int]]:
    files = [chess.square_file(sq) for sq in board.pieces(chess.PAWN, color)]
    weak = {("doubled", f) for f in files if files.count(f) > 1}
    king = board.king(color)
    # Only a king tucked on a wing has a pawn shelter to lose; a centred king never had one.
    if (
        king is not None
        and chess.square_rank(king) in _KING_HOME_RANKS[color]
        and chess.square_file(king) not in _CENTRE_FILES
    ):
        king_file = chess.square_file(king)
        weak |= {
            ("king_shelter", f)
            for f in (king_file - 1, king_file, king_file + 1)
            if 0 <= f <= 7 and f not in files
        }
    return weak


def _settled_line_end(
    board: chess.Board, best_line: list[str] | None
) -> list[chess.Board]:
    best_boards = line_boards(board, best_line or [])
    # Like material: a line that ends on a capture the opponent can take back hasn't
    # settled, so judge the structure before that capture.
    if len(best_boards) > 1 and final_capture_at_risk(best_boards[-1], board.turn):
        return best_boards[:-1]
    return best_boards


def _refuted_board(
    board: chess.Board, blunder_move: chess.Move, refutation_line: list[str] | None
) -> chess.Board:
    after_blunder = board.copy(stack=False)
    after_blunder.push(blunder_move)
    return (line_boards(after_blunder, refutation_line or []) or [after_blunder])[-1]


def _new_pawn_damage(
    board: chess.Board, line_end: chess.Board, refuted: chess.Board
) -> set[tuple[str, int]]:
    opponent = not board.turn
    damage = (
        _pawn_weaknesses(line_end, opponent)
        - _pawn_weaknesses(board, opponent)
        - _pawn_weaknesses(refuted, opponent)
    )
    # A king that walks to an unguarded square chose that; only cover stripped from
    # under a king that stayed put is damage the line inflicted.
    if line_end.king(opponent) != board.king(opponent):
        return {w for w in damage if w[0] != "king_shelter"}
    return damage


def explain_best_structure(
    board: chess.Board,
    blunder_move: chess.Move,
    best_line: list[str] | None,
    refutation_line: list[str] | None,
) -> I18nMessage | None:
    """Pawn damage the best line inflicts on the opponent that the blunder's refutation
    doesn't: the reason a quiet trade like Bxf3 gxf3 is best."""
    best_boards = _settled_line_end(board, best_line)
    if not best_line or not best_boards:
        return None
    damage = _new_pawn_damage(
        board, best_boards[-1], _refuted_board(board, blunder_move, refutation_line)
    )
    if not damage:
        return None
    kind, file_index = min(
        damage, key=lambda w: (_PAWN_DAMAGE_PRIORITY.index(w[0]), w[1])
    )
    plies = next(
        ply
        for ply, line_board in enumerate(best_boards, start=1)
        if (kind, file_index) in _pawn_weaknesses(line_board, not board.turn)
    )
    return I18nMessage(
        key=_PAWN_DAMAGE_KEYS[kind],
        params={
            "line": " ".join(best_line[:plies]),
            "file": chess.FILE_NAMES[file_index],
        },
    )
