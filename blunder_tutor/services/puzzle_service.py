from __future__ import annotations

from dataclasses import dataclass

import chess

from blunder_tutor.errors import IllegalMoveError
from blunder_tutor.services.analysis_service import AnalysisService, PositionAnalysis
from blunder_tutor.trainer import BlunderFilter, BlunderPuzzle, Trainer
from blunder_tutor.utils.chess_utils import board_from_fen, format_eval


@dataclass
class PuzzleWithAnalysis:
    puzzle: BlunderPuzzle
    analysis: PositionAnalysis


@dataclass
class GradedAttempt:
    puzzle: BlunderPuzzle
    user_uci: str
    user_san: str
    user_eval_cp: int
    is_best: bool
    is_blunder: bool


class PuzzleService:
    def __init__(self, trainer: Trainer, analysis_service: AnalysisService):
        self.trainer = trainer
        self.analysis_service = analysis_service

    async def get_puzzle_with_analysis(
        self,
        criteria: BlunderFilter | None = None,
    ) -> PuzzleWithAnalysis:
        puzzle = await self.trainer.pick_random_blunder(criteria or BlunderFilter())

        if puzzle.best_move_uci and puzzle.best_move_san and puzzle.best_line:
            best_line_list = puzzle.best_line.split()
            analysis = PositionAnalysis(
                eval_cp=puzzle.eval_before,
                eval_display=format_eval(puzzle.eval_before),
                best_move_uci=puzzle.best_move_uci,
                best_move_san=puzzle.best_move_san,
                best_line=best_line_list,
            )
        else:
            analysis = await self.analysis_service.analyze_position(
                fen=puzzle.fen, player_color=puzzle.player_color
            )

        return PuzzleWithAnalysis(puzzle=puzzle, analysis=analysis)

    async def get_specific_puzzle(self, game_id: str, ply: int) -> PuzzleWithAnalysis:
        puzzle = await self.trainer.get_specific_blunder(game_id, ply)

        if puzzle.best_move_uci and puzzle.best_move_san and puzzle.best_line:
            best_line_list = puzzle.best_line.split()
            analysis = PositionAnalysis(
                eval_cp=puzzle.eval_before,
                eval_display=format_eval(puzzle.eval_before),
                best_move_uci=puzzle.best_move_uci,
                best_move_san=puzzle.best_move_san,
                best_line=best_line_list,
            )
        else:
            analysis = await self.analysis_service.analyze_position(
                fen=puzzle.fen, player_color=puzzle.player_color
            )

        return PuzzleWithAnalysis(puzzle=puzzle, analysis=analysis)

    async def grade_attempt(self, game_id: str, ply: int, move: str) -> GradedAttempt:
        """Grades against the stored puzzle only; nothing about the position or the
        right answer comes from the client, and no engine re-analysis can shift it."""
        # shortcut: a legacy row without a stored best move can't be graded as best;
        # every current analysis stores one. Persist the fallback if that changes.
        puzzle = await self.trainer.get_specific_blunder(game_id, ply)
        board = board_from_fen(puzzle.fen)
        user_move = _parse_legal_move(board, move)
        user_uci = board.uci(user_move)

        is_best = _is_same_move(board, user_move, puzzle.best_move_uci)
        is_blunder = _is_same_move(board, user_move, puzzle.blunder_uci)
        return GradedAttempt(
            puzzle=puzzle,
            user_uci=user_uci,
            user_san=board.san(user_move),
            user_eval_cp=await self._user_eval_cp(
                puzzle, user_uci, is_best, is_blunder
            ),
            is_best=is_best,
            is_blunder=is_blunder,
        )

    async def _user_eval_cp(
        self, puzzle: BlunderPuzzle, move: str, is_best: bool, is_blunder: bool
    ) -> int:
        if is_blunder:
            return puzzle.eval_after
        if is_best and puzzle.best_move_eval is not None:
            return puzzle.best_move_eval
        evaluation = await self.analysis_service.evaluate_move(puzzle.fen, move)
        return evaluation.eval_cp


def _parse_legal_move(board: chess.Board, move_uci: str) -> chess.Move:
    try:
        move = board.parse_uci(move_uci)
    except ValueError as exc:
        raise IllegalMoveError(move_uci) from exc
    # parse_uci lets the null move "0000" through.
    if move not in board.legal_moves:
        raise IllegalMoveError(move_uci)
    return move


def _is_same_move(board: chess.Board, move: chess.Move, stored_uci: str | None) -> bool:
    # Compare parsed moves, not strings: castling has two UCI spellings (e1g1 vs the
    # Chess960 king-takes-rook e1h1) and parse_uci maps both to the same move.
    if not stored_uci:
        return False
    try:
        return board.parse_uci(stored_uci) == move
    except ValueError:
        return False
