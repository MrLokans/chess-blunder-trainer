from __future__ import annotations

from dataclasses import dataclass
from functools import cached_property

import chess


@dataclass(frozen=True)
class Puzzle:
    board: chess.Board
    blunder_move: chess.Move
    best_move: chess.Move | None
    cp_loss: int
    best_line: list[str] | None = None
    refutation_line: list[str] | None = None

    @property
    def player(self) -> chess.Color:
        return self.board.turn

    @cached_property
    def board_after_blunder(self) -> chess.Board:
        board_after = self.board.copy()
        board_after.push(self.blunder_move)
        return board_after
