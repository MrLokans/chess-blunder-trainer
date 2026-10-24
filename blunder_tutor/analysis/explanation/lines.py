from __future__ import annotations

from dataclasses import dataclass, field

import chess

from blunder_tutor.analysis.explanation.board import (
    MINOR_PIECE_VALUE,
    material_balance,
    piece_value,
)


@dataclass(frozen=True)
class _PVCapture:
    piece_type: chess.PieceType
    by_color: chess.Color


@dataclass
class _PVWalkState:
    line_board: chess.Board
    player_caps: list[_PVCapture] = field(default_factory=list)
    opp_caps: list[_PVCapture] = field(default_factory=list)
    gives_mate: bool = False


@dataclass(frozen=True)
class PVAnalysis:
    moves_san: list[str]
    gives_check: bool
    gives_mate: bool
    balance_gain: int
    player_captures: list[_PVCapture]
    opponent_captures: list[_PVCapture]
    assumed_recapture: chess.PieceType | None = None

    @property
    def is_sacrifice_combination(self) -> bool:
        return bool(self.opponent_captures) and self.balance_gain >= 3

    @property
    def net_piece_won(self) -> chess.PieceType | None:
        if self.balance_gain < 1:
            return None
        # Cancel like-for-like trades first: trading queens while also taking a knight
        # wins a knight, not a queen.
        won = [cap.piece_type for cap in self.player_captures]
        lost = [cap.piece_type for cap in self.opponent_captures]
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


def _record_capture_if_any(
    state: _PVWalkState,
    prev_board: chess.Board,
    move: chess.Move,
    side: chess.Color,
    player: chess.Color,
) -> None:
    if not prev_board.is_capture(move):
        return
    captured = prev_board.piece_at(move.to_square)
    if captured is None:
        return
    cap = _PVCapture(captured.piece_type, side)
    if side == player:
        state.player_caps.append(cap)
    else:
        state.opp_caps.append(cap)


def _walk_pv_continuation(
    state: _PVWalkState,
    best_line: list[str],
    player: chess.Color,
) -> bool:
    for move_san in best_line[1:]:
        prev_board = state.line_board.copy()
        try:
            move = state.line_board.parse_san(move_san)
        except ValueError, chess.IllegalMoveError:
            return False
        side = state.line_board.turn
        state.line_board.push(move)
        _record_capture_if_any(state, prev_board, move, side, player)
        if state.line_board.is_checkmate():
            state.gives_mate = True
            return True
    return True


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


def analyze_pv(
    board: chess.Board,
    best_move: chess.Move,
    best_line: list[str],
) -> PVAnalysis | None:
    player = board.turn
    state = _PVWalkState(line_board=board.copy())
    balance_before = material_balance(board, player)

    try:
        state.line_board.push(best_move)
    except ValueError, chess.IllegalMoveError:
        return None

    gives_check = state.line_board.is_check()
    if state.line_board.is_checkmate():
        state.gives_mate = True
    if board.is_capture(best_move):
        captured = board.piece_at(best_move.to_square)
        if captured:
            state.player_caps.append(_PVCapture(captured.piece_type, player))

    walked_cleanly = state.gives_mate or _walk_pv_continuation(state, best_line, player)
    # If SAN parse fails mid-line with nothing captured and no check, the PV is too
    # unreliable; fall back to the static layer.
    if not walked_cleanly and not state.player_caps and not gives_check:
        return None

    at_risk = final_capture_at_risk(state.line_board, player)
    at_risk_value = piece_value(at_risk) if at_risk else 0
    return PVAnalysis(
        moves_san=best_line,
        gives_check=gives_check,
        gives_mate=state.gives_mate,
        balance_gain=material_balance(state.line_board, player)
        - balance_before
        - at_risk_value,
        player_captures=state.player_caps,
        opponent_captures=state.opp_caps,
        assumed_recapture=at_risk,
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
