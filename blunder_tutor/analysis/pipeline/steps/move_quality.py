from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

import chess
import chess.engine

from blunder_tutor.analysis.pipeline.context import StepResult
from blunder_tutor.analysis.pipeline.steps.base import AnalysisStep
from blunder_tutor.analysis.thresholds import winning_chances
from blunder_tutor.constants import MAX_CP_LOSS

if TYPE_CHECKING:
    from blunder_tutor.analysis.pipeline.context import StepContext
    from blunder_tutor.analysis.thresholds import Thresholds


def _is_mate_score(score: chess.engine.PovScore, side: chess.Color) -> bool:
    pov = score.pov(side)
    return pov.is_mate()


def _get_mate_depth(score: chess.engine.PovScore, side: chess.Color) -> int | None:
    pov = score.pov(side)
    return pov.mate() if pov.is_mate() else None


def _classify_wc(wc_loss: float, thresholds: Thresholds) -> str:
    if wc_loss >= thresholds.wc_blunder:
        return "blunder"
    if wc_loss >= thresholds.wc_mistake:
        return "mistake"
    if wc_loss >= thresholds.wc_inaccuracy:
        return "inaccuracy"
    return "good"


# Mate-transition thresholds (from Lichess Advice.scala).
_MATE_CP_INACCURACY = -999
_MATE_CP_MISTAKE = -700


def _classify_mate_created(prev_pov_cp: int) -> str:
    if prev_pov_cp < _MATE_CP_INACCURACY:
        return "inaccuracy"
    if prev_pov_cp < _MATE_CP_MISTAKE:
        return "mistake"
    return "blunder"


def _classify_mate_lost(current_pov_cp: int) -> str:
    if current_pov_cp > -_MATE_CP_INACCURACY:
        return "inaccuracy"
    if current_pov_cp > -_MATE_CP_MISTAKE:
        return "mistake"
    return "blunder"


def _class_to_int(label: str) -> int:
    return {"good": 0, "inaccuracy": 1, "mistake": 2, "blunder": 3}[label]


def compute_difficulty(
    board: chess.Board,
    best_move_uci: str | None,
    cp_loss: int,
    classification: int,
) -> int:
    if classification < _class_to_int("inaccuracy"):
        return 0

    if not best_move_uci:
        return 50

    try:
        best_move = chess.Move.from_uci(best_move_uci)
    except ValueError:
        return 50

    score = 0

    # Quiet (non-forcing) best moves are harder to find
    is_capture = board.is_capture(best_move)
    gives_check = board.gives_check(best_move)
    if not is_capture and not gives_check:
        score += 40
    elif is_capture and not gives_check:
        score += 15
    else:
        score += 5

    # Fewer safe alternatives → harder position (less choice = more forgivable)
    legal_count = board.legal_moves.count()
    if legal_count <= 3:
        score += 30
    elif legal_count <= 8:
        score += 20
    elif legal_count <= 15:
        score += 10

    # Very large cp_loss with a quiet best move suggests a deep tactic
    if cp_loss >= 400 and not is_capture and not gives_check:
        score += 15

    return min(score, 100)


class MoveQualityStep(AnalysisStep):
    @property
    def step_id(self) -> str:
        return "move_quality"

    @property
    def depends_on(self) -> frozenset[str]:
        return frozenset({"stockfish"})

    async def execute(self, ctx: StepContext) -> StepResult:
        stockfish_result = ctx.get_step_result("stockfish")
        if not stockfish_result or not stockfish_result.success:
            return StepResult(
                step_id=self.step_id,
                success=False,
                error="Stockfish step not completed",
            )

        move_evals = stockfish_result.data.get("move_evals", [])
        thresholds = ctx.thresholds

        moves: list[dict] = []
        for move_data in move_evals:
            eval_before = move_data["eval_before"]
            eval_after = move_data["eval_after"]
            info_before = move_data["info_before"]
            player = chess.WHITE if move_data["player"] == "white" else chess.BLACK

            missed_mate_depth: int | None = None

            if eval_after == 100000:  # Checkmate delivered
                delta = 0
                cp_loss = 0
                class_label = "good"
            else:
                delta = eval_before - eval_after
                cp_loss = min(max(0, delta), MAX_CP_LOSS)

                mate_before = _get_mate_depth(info_before["score"], player)
                has_winning_mate_before = mate_before is not None and mate_before > 0
                is_mate_before = mate_before is not None

                # Detect mate-after from eval (score_to_cp uses mate_score=100000)
                is_mate_after = abs(eval_after) >= 90000
                has_winning_mate_after = is_mate_after and eval_after > 0
                has_losing_mate_after = is_mate_after and eval_after < 0

                if has_winning_mate_before:
                    missed_mate_depth = mate_before

                # Mate transition types (Lichess Advice.scala)
                mate_created = not is_mate_before and has_losing_mate_after
                mate_lost = (
                    has_winning_mate_before
                    and not has_winning_mate_after
                    and not has_losing_mate_after
                )
                mate_delayed = has_winning_mate_before and has_losing_mate_after

                if mate_created:
                    class_label = _classify_mate_created(eval_before)
                elif mate_lost:
                    class_label = _classify_mate_lost(eval_after)
                elif mate_delayed:
                    class_label = "blunder"
                else:
                    wc_before = winning_chances(eval_before)
                    wc_after = winning_chances(eval_after)
                    wc_loss = max(0.0, wc_before - wc_after)
                    class_label = _classify_wc(wc_loss, thresholds)

            classification = _class_to_int(class_label)
            board = move_data.get("board")
            difficulty = (
                compute_difficulty(
                    board, move_data["best_move_uci"], cp_loss, classification
                )
                if board is not None
                else None
            )

            moves.append(
                {
                    "ply": move_data["ply"],
                    "move_number": move_data["move_number"],
                    "player": move_data["player"],
                    "uci": move_data["uci"],
                    "san": move_data["san"],
                    "eval_before": eval_before,
                    "eval_after": eval_after,
                    "delta": delta,
                    "cp_loss": cp_loss,
                    "classification": classification,
                    "best_move_uci": move_data["best_move_uci"],
                    "best_move_san": move_data["best_move_san"],
                    "best_line": move_data["best_line"],
                    "best_move_eval": move_data["best_move_eval"],
                    "difficulty": difficulty,
                    "missed_mate_depth": missed_mate_depth,
                }
            )

        return StepResult(
            step_id=self.step_id,
            success=True,
            data={"moves": moves, "analyzed_at": datetime.now(UTC).isoformat()},
        )
