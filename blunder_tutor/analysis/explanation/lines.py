from __future__ import annotations

from dataclasses import dataclass
from itertools import pairwise

import chess

from blunder_tutor.analysis.explanation.board import (
    MINOR_PIECE_VALUE,
    material_balance,
    piece_value,
)


@dataclass(frozen=True)
class PVAnalysis:
    moves_san: list[str]
    gives_mate: bool
    balance_gain: int
    player_captures: list[chess.PieceType]
    opponent_captures: list[chess.PieceType]
    assumed_recapture: chess.PieceType | None = None
    perpetual_check: bool = False

    @property
    def is_sacrifice_combination(self) -> bool:
        return bool(self.opponent_captures) and self.balance_gain >= 3

    @property
    def net_piece_won(self) -> chess.PieceType | None:
        if self.balance_gain < 1:
            return None
        # Cancel like-for-like trades first: trading queens while also taking a knight
        # wins a knight, not a queen.
        won = list(self.player_captures)
        lost = list(self.opponent_captures)
        if self.assumed_recapture is not None:
            lost.append(self.assumed_recapture)
        for lost_type in lost:
            traded = next(
                (pt for pt in won if piece_value(pt) == piece_value(lost_type)), None
            )
            if traded is not None:
                won.remove(traded)
        named = max(won, key=piece_value, default=None)
        # Don't name a piece won back with much more given up elsewhere (a queen for
        # a rook and two pawns); the generic combination wording fits instead.
        if named is None or piece_value(named) - self.balance_gain > MINOR_PIECE_VALUE:
            return None
        return named


def final_capture_at_risk(
    line_board: chess.Board, player: chess.Color
) -> chess.PieceType | None:
    """A line cut off mid-exchange: when it ends on the player's capture and the
    opponent can profitably take the capturer back, assume it will be."""
    last = line_board.pop()
    is_capture = line_board.is_capture(last)
    line_board.push(last)
    capturer = line_board.piece_at(last.to_square)
    if not is_capture or capturer is None or capturer.color != player:
        return None
    recapturers = [
        line_board.piece_at(move.from_square)
        for move in line_board.legal_moves
        if move.to_square == last.to_square
    ]
    if not recapturers:
        return None
    cheapest = min(piece_value(piece.piece_type) for piece in recapturers if piece)
    defended = bool(line_board.attackers(player, last.to_square))
    if defended and cheapest > piece_value(capturer.piece_type):
        return None
    return capturer.piece_type


def _captured_piece(before: chess.Board, after: chess.Board) -> chess.PieceType | None:
    move = after.peek()
    if not before.is_capture(move):
        return None
    captured = before.piece_at(move.to_square)
    return captured.piece_type if captured else None


def _captures_by_side(
    boards: list[chess.Board], player: chess.Color
) -> tuple[list[chess.PieceType], list[chess.PieceType]]:
    player_captures: list[chess.PieceType] = []
    opponent_captures: list[chess.PieceType] = []
    for before, after in pairwise(boards):
        captured = _captured_piece(before, after)
        if captured is not None:
            side = player_captures if before.turn == player else opponent_captures
            side.append(captured)
    return player_captures, opponent_captures


def _settled_balance_gain(
    board: chess.Board, line_end: chess.Board, player: chess.Color
) -> tuple[int, chess.PieceType | None]:
    at_risk = final_capture_at_risk(line_end, player)
    at_risk_value = piece_value(at_risk) if at_risk else 0
    gain = material_balance(line_end, player) - material_balance(board, player)
    return gain - at_risk_value, at_risk


def _replay(
    board: chess.Board, first_move: chess.Move, rest_san: list[str]
) -> list[chess.Board]:
    first = board.copy()
    first.push(first_move)
    return [first, *line_boards(first, rest_san)]


def _position_key(board: chess.Board) -> str:
    return board.fen().rsplit(" ", 2)[0]


def _is_perpetual_check(board: chess.Board, boards: list[chess.Board]) -> bool:
    """Every move of the player's gives check and the line returns to a position it
    already had: the engine is holding a draw by repetition."""
    player_boards = boards[::2]
    if len(boards) < 3 or not all(b.is_check() for b in player_boards):
        return False
    earlier = {_position_key(b) for b in (board, *boards[:-1])}
    return _position_key(boards[-1]) in earlier


def analyze_pv(
    board: chess.Board,
    best_move: chess.Move,
    best_line: list[str],
) -> PVAnalysis | None:
    player = board.turn
    boards = _replay(board, best_move, best_line[1:])
    player_captures, opponent_captures = _captures_by_side([board, *boards], player)
    gives_mate = boards[-1].is_checkmate()
    # A line whose SAN stops parsing early, with nothing captured and no check, is too
    # unreliable to explain from; fall back to the static layer.
    parsed_fully = gives_mate or len(boards) == len(best_line)
    if not parsed_fully and not player_captures and not boards[0].is_check():
        return None
    balance_gain, at_risk = _settled_balance_gain(board, boards[-1], player)
    return PVAnalysis(
        moves_san=best_line,
        gives_mate=gives_mate,
        balance_gain=balance_gain,
        player_captures=player_captures,
        opponent_captures=opponent_captures,
        assumed_recapture=at_risk,
        perpetual_check=_is_perpetual_check(board, boards),
    )


def format_line(moves: list[str], max_moves: int = 5) -> str:
    return " ".join(moves[:max_moves])


def line_boards(board: chess.Board, moves_san: list[str]) -> list[chess.Board]:
    boards = []
    line_board = board.copy()
    for san in moves_san:
        try:
            line_board.push_san(san)
        except ValueError:
            break
        boards.append(line_board.copy())
    return boards
