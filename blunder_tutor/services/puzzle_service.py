from __future__ import annotations

from dataclasses import dataclass

from blunder_tutor.services.analysis_service import AnalysisService, PositionAnalysis
from blunder_tutor.trainer import BlunderPuzzle, Trainer


@dataclass
class PuzzleWithAnalysis:
    puzzle: BlunderPuzzle
    analysis: PositionAnalysis


class PuzzleService:
    def __init__(self, trainer: Trainer, analysis_service: AnalysisService):
        self.trainer = trainer
        self.analysis_service = analysis_service

    async def get_puzzle_with_analysis(
        self,
        username: str | list[str],
        source: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        exclude_recently_solved: bool = True,
        spaced_repetition_days: int = 30,
        game_phases: list[int] | None = None,
    ) -> PuzzleWithAnalysis:
        puzzle = await self.trainer.pick_random_blunder(
            username=username,
            source=source,
            start_date=start_date,
            end_date=end_date,
            exclude_recently_solved=exclude_recently_solved,
            spaced_repetition_days=spaced_repetition_days,
            game_phases=game_phases,
        )

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

        return PuzzleWithAnalysis(puzzle=puzzle, analysis=analysis)

    def _format_eval(self, eval_cp: int, player_color: str) -> str:
        from blunder_tutor.utils.chess_utils import format_eval

        return format_eval(eval_cp, player_color)
