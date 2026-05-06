from __future__ import annotations

from dataclasses import dataclass

from blunder_tutor.services.analysis_service import (
    AnalysisService,
    PositionAnalysis,
    PunishmentAnalysis,
)
from blunder_tutor.trainer import BlunderFilter, BlunderPuzzle, Trainer
from blunder_tutor.utils.chess_utils import format_eval


@dataclass
class PuzzleWithAnalysis:
    puzzle: BlunderPuzzle
    analysis: PositionAnalysis
    punishment: PunishmentAnalysis | None = None


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
                eval_display=self._format_eval(puzzle.eval_before, puzzle.player_color),
                best_move_uci=puzzle.best_move_uci,
                best_move_san=puzzle.best_move_san,
                best_line=best_line_list,
            )
        else:
            analysis = await self.analysis_service.analyze_position(
                fen=puzzle.fen, player_color=puzzle.player_color
            )

        punishment = await self._get_punishment_analysis(puzzle, analysis)
        return PuzzleWithAnalysis(puzzle=puzzle, analysis=analysis, punishment=punishment)

    async def get_specific_puzzle(self, game_id: str, ply: int) -> PuzzleWithAnalysis:
        puzzle = await self.trainer.get_specific_blunder(game_id, ply)

        if puzzle.best_move_uci and puzzle.best_move_san and puzzle.best_line:
            best_line_list = puzzle.best_line.split()
            analysis = PositionAnalysis(
                eval_cp=puzzle.eval_before,
                eval_display=self._format_eval(puzzle.eval_before, puzzle.player_color),
                best_move_uci=puzzle.best_move_uci,
                best_move_san=puzzle.best_move_san,
                best_line=best_line_list,
            )
        else:
            analysis = await self.analysis_service.analyze_position(
                fen=puzzle.fen, player_color=puzzle.player_color
            )

        punishment = await self._get_punishment_analysis(puzzle, analysis)
        return PuzzleWithAnalysis(puzzle=puzzle, analysis=analysis, punishment=punishment)

    async def _get_punishment_analysis(
        self, puzzle: BlunderPuzzle, analysis: PositionAnalysis
    ) -> PunishmentAnalysis | None:
        try:
            return await self.analysis_service.analyze_punishment_line(
                fen=puzzle.fen,
                blunder_uci=puzzle.blunder_uci,
                player_color=puzzle.player_color,
                best_move_san=analysis.best_move_san,
                cp_loss=puzzle.cp_loss,
            )
        except (ValueError, RuntimeError):
            return None

    def _format_eval(self, eval_cp: int, player_color: str) -> str:
        return format_eval(eval_cp, player_color)
