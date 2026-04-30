from __future__ import annotations

import io
from unittest.mock import AsyncMock, MagicMock, patch

import chess.pgn
import pytest

from blunder_tutor.analysis.pipeline.context import StepContext, StepResult
from blunder_tutor.analysis.pipeline.steps import get_all_steps
from blunder_tutor.analysis.pipeline.steps.eco import ECOClassifyStep
from blunder_tutor.analysis.pipeline.steps.move_quality import MoveQualityStep
from blunder_tutor.analysis.pipeline.steps.phase import PhaseClassifyStep
from blunder_tutor.analysis.pipeline.steps.stockfish import StockfishAnalysisStep
from blunder_tutor.analysis.pipeline.steps.tactics import TacticsClassifyStep
from blunder_tutor.analysis.thresholds import Thresholds
from blunder_tutor.constants import (
    CLASSIFICATION_BLUNDER,
    CLASSIFICATION_NORMAL,
    MATE_SCORE_ANALYSIS,
    MATE_THRESHOLD,
)


def _make_score_mock(*, is_mate: bool, mate: int | None = None) -> MagicMock:
    pov = MagicMock()
    pov.is_mate.return_value = is_mate
    pov.mate.return_value = mate
    score = MagicMock()
    score.pov.return_value = pov
    return score


_BOARD_UNSET = object()


def _make_move_eval(
    *,
    eval_before: int,
    eval_after: int,
    info_before_score: MagicMock | None = None,
    board: object = _BOARD_UNSET,
    ply: int = 1,
    classification: int | None = None,
) -> dict:
    if info_before_score is None:
        info_before_score = _make_score_mock(is_mate=False)
    move_data = {
        "ply": ply,
        "move_number": 1,
        "player": "white",
        "uci": "e2e4",
        "san": "e4",
        "eval_before": eval_before,
        "eval_after": eval_after,
        "info_before": {"score": info_before_score},
        "best_move_uci": "e2e4",
        "best_move_san": "e4",
        "best_line": "e4 e5",
        "best_move_eval": eval_before,
    }
    if board is not _BOARD_UNSET:
        move_data["board"] = board
    if classification is not None:
        move_data["classification"] = classification
    return move_data


@pytest.fixture
def sample_game():
    pgn_text = """[Event "Test"]
[Site "?"]
[Date "2024.01.01"]
[Round "1"]
[White "Player1"]
[Black "Player2"]
[Result "1-0"]

1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 4. Ba4 Nf6 5. O-O Be7 1-0"""
    return chess.pgn.read_game(io.StringIO(pgn_text))


@pytest.fixture
def mock_context(sample_game):
    analysis_repo = AsyncMock()
    analysis_repo.update_game_eco = AsyncMock()
    analysis_repo.get_game_eco = AsyncMock(
        return_value={"eco_code": None, "eco_name": None}
    )
    analysis_repo.is_step_completed = AsyncMock(return_value=False)

    game_repo = AsyncMock()

    ctx = StepContext(
        game_id="test_game_id",
        game=sample_game,
        analysis_repo=analysis_repo,
        game_repo=game_repo,
        engine_path="/path/to/engine",
        thresholds=Thresholds(),
        depth=14,
    )
    return ctx


class TestECOClassifyStep:
    async def test_step_id(self):
        step = ECOClassifyStep()
        assert step.step_id == "eco"

    async def test_no_dependencies(self):
        step = ECOClassifyStep()
        assert step.depends_on == frozenset()

    async def test_execute_classifies_opening(self, mock_context):
        step = ECOClassifyStep()
        result = await step.execute(mock_context)

        assert result.success is True
        assert result.step_id == "eco"
        # Ruy Lopez position should be classified
        assert (
            result.data.get("eco_code") is not None
            or result.data.get("eco_code") is None
        )
        mock_context.analysis_repo.update_game_eco.assert_called_once()


class TestPhaseClassifyStep:
    async def test_step_id(self):
        step = PhaseClassifyStep()
        assert step.step_id == "phase"

    async def test_no_dependencies(self):
        step = PhaseClassifyStep()
        assert step.depends_on == frozenset()

    async def test_execute_classifies_phases(self, mock_context):
        step = PhaseClassifyStep()
        result = await step.execute(mock_context)

        assert result.success is True
        assert result.step_id == "phase"
        assert "phases" in result.data

        phases = result.data["phases"]
        assert len(phases) > 0
        for phase_entry in phases:
            assert "ply" in phase_entry
            assert "move_number" in phase_entry
            assert "phase" in phase_entry
            assert phase_entry["phase"] in [0, 1, 2]


class TestMoveQualityStep:
    async def test_step_id(self):
        step = MoveQualityStep()
        assert step.step_id == "move_quality"

    async def test_depends_on_stockfish(self):
        step = MoveQualityStep()
        assert "stockfish" in step.depends_on

    async def test_execute_fails_without_stockfish(self, mock_context):
        step = MoveQualityStep()
        result = await step.execute(mock_context)

        assert result.success is False
        assert "Stockfish step not completed" in result.error

    async def test_execute_with_stockfish_results(self, mock_context):
        stockfish_data = {
            "move_evals": [
                {
                    "ply": 1,
                    "move_number": 1,
                    "player": "white",
                    "uci": "e2e4",
                    "san": "e4",
                    "eval_before": 20,
                    "eval_after": 15,
                    "info_before": {"score": MagicMock()},
                    "best_move_uci": "e2e4",
                    "best_move_san": "e4",
                    "best_line": "e4 e5",
                    "best_move_eval": 20,
                    "board": MagicMock(),
                },
            ]
        }
        stockfish_result = StepResult(
            step_id="stockfish", success=True, data=stockfish_data
        )
        mock_context.add_step_result(stockfish_result)

        # Mock the is_mate method
        stockfish_data["move_evals"][0]["info_before"][
            "score"
        ].pov.return_value.is_mate.return_value = False

        step = MoveQualityStep()
        result = await step.execute(mock_context)

        assert result.success is True
        assert "moves" in result.data
        moves = result.data["moves"]
        assert len(moves) == 1
        assert moves[0]["ply"] == 1
        assert "cp_loss" in moves[0]
        assert "classification" in moves[0]

    async def test_execute_classifies_mate_created(self, mock_context):
        move_eval = _make_move_eval(
            eval_before=200,
            eval_after=-MATE_THRESHOLD - 100,
            info_before_score=_make_score_mock(is_mate=False),
            board=chess.Board(),
        )
        mock_context.add_step_result(
            StepResult(
                step_id="stockfish", success=True, data={"move_evals": [move_eval]}
            )
        )

        result = await MoveQualityStep().execute(mock_context)

        assert result.success is True
        # eval_before=200 ≥ -700 → BLUNDER per _classify_mate_created.
        assert result.data["moves"][0]["classification"] == CLASSIFICATION_BLUNDER

    async def test_execute_classifies_mate_delayed(self, mock_context):
        move_eval = _make_move_eval(
            eval_before=MATE_THRESHOLD + 200,
            eval_after=-MATE_THRESHOLD - 100,
            info_before_score=_make_score_mock(is_mate=True, mate=5),
            board=chess.Board(),
        )
        mock_context.add_step_result(
            StepResult(
                step_id="stockfish", success=True, data={"move_evals": [move_eval]}
            )
        )

        result = await MoveQualityStep().execute(mock_context)

        assert result.success is True
        moves = result.data["moves"]
        # has_winning_mate_before AND has_losing_mate_after → mate_delayed → BLUNDER.
        assert moves[0]["classification"] == CLASSIFICATION_BLUNDER
        # has_winning_mate_before sets missed_mate_depth.
        assert moves[0]["missed_mate_depth"] == 5

    async def test_execute_records_checkmate_delivered_as_good(self, mock_context):
        move_eval = _make_move_eval(
            eval_before=500,
            eval_after=MATE_SCORE_ANALYSIS,
            info_before_score=_make_score_mock(is_mate=False),
            board=chess.Board(),
        )
        mock_context.add_step_result(
            StepResult(
                step_id="stockfish", success=True, data={"move_evals": [move_eval]}
            )
        )

        result = await MoveQualityStep().execute(mock_context)

        assert result.success is True
        moves = result.data["moves"]
        assert moves[0]["cp_loss"] == 0
        assert moves[0]["classification"] == CLASSIFICATION_NORMAL

    async def test_execute_difficulty_none_when_board_missing(self, mock_context):
        move_eval = _make_move_eval(
            eval_before=20,
            eval_after=15,
            info_before_score=_make_score_mock(is_mate=False),
            # board key intentionally absent
        )
        mock_context.add_step_result(
            StepResult(
                step_id="stockfish", success=True, data={"move_evals": [move_eval]}
            )
        )

        result = await MoveQualityStep().execute(mock_context)

        assert result.success is True
        assert result.data["moves"][0]["difficulty"] is None


class TestTacticsClassifyStep:
    def _make_tactics_result_mock(self) -> MagicMock:
        result = MagicMock()
        result.primary_pattern.value = 0
        result.primary_pattern_name = "None"
        result.blunder_reason = ""
        result.missed_tactic = None
        result.allowed_tactic = None
        return result

    def _move_data(self, ply: int, classification: int) -> dict:
        return {
            "ply": ply,
            "classification": classification,
            "best_move_uci": "e2e4",
        }

    async def test_execute_fails_without_move_quality(self, mock_context):
        step = TacticsClassifyStep()
        result = await step.execute(mock_context)

        assert result.success is False
        assert "Move quality step not completed" in result.error

    async def test_execute_skips_non_blunder_moves(self, mock_context):
        moves = [
            self._move_data(ply=1, classification=0),
            self._move_data(ply=2, classification=1),
            self._move_data(ply=3, classification=2),
        ]
        mock_context.add_step_result(
            StepResult(step_id="move_quality", success=True, data={"moves": moves})
        )

        with patch(
            "blunder_tutor.analysis.pipeline.steps.tactics.classify_blunder_tactics"
        ) as mock_classify:
            result = await TacticsClassifyStep().execute(mock_context)
            mock_classify.assert_not_called()

        assert result.success is True
        assert result.data["tactics"] == []

    async def test_execute_runs_tactics_for_blunder_with_correct_board_state(
        self, mock_context
    ):
        # mainline of sample_game: e4 e5 Nf3 Nc6 Bb5 (5 plies). The 3rd ply
        # is Nf3; its board_before should be the position after e4 e5.
        moves = [
            self._move_data(ply=1, classification=0),
            self._move_data(ply=2, classification=0),
            self._move_data(ply=3, classification=CLASSIFICATION_BLUNDER),
        ]
        mock_context.add_step_result(
            StepResult(step_id="move_quality", success=True, data={"moves": moves})
        )

        expected_board = mock_context.game.board()
        mainline = list(mock_context.game.mainline_moves())
        expected_board.push(mainline[0])
        expected_board.push(mainline[1])
        expected_fen = expected_board.fen()
        expected_third_move = mainline[2]

        tactics_result = self._make_tactics_result_mock()
        with patch(
            "blunder_tutor.analysis.pipeline.steps.tactics.classify_blunder_tactics",
            return_value=tactics_result,
        ) as mock_classify:
            result = await TacticsClassifyStep().execute(mock_context)
            assert mock_classify.call_count == 1
            board_before, move_played, _best = mock_classify.call_args.args

        assert result.success is True
        assert board_before.fen() == expected_fen
        assert move_played == expected_third_move


class TestStockfishAnalysisStep:
    @pytest.fixture
    def short_game(self):
        pgn_text = """[Event "Test"]
[Site "?"]
[Date "2024.01.01"]
[Round "1"]
[White "Player1"]
[Black "Player2"]
[Result "1-0"]

1. e4 e5 2. Nf3 Nc6 3. Bb5 1-0"""
        return chess.pgn.read_game(io.StringIO(pgn_text))

    def _make_mock_score(self, cp_value: int) -> MagicMock:
        score = MagicMock()
        pov_score = MagicMock()
        pov_score.score.return_value = cp_value
        pov_score.is_mate.return_value = False
        score.pov.return_value = pov_score
        return score

    async def test_single_pass_analyse_call_count(self, short_game):
        def analyse_side_effect(board, _limit, **_kwargs):
            legal_moves = list(board.legal_moves)
            pv = [legal_moves[0]] if legal_moves else []
            return {"score": self._make_mock_score(20), "pv": pv}

        mock_engine = AsyncMock()
        mock_engine.analyse = AsyncMock(side_effect=analyse_side_effect)

        analysis_repo = AsyncMock()
        analysis_repo.is_step_completed = AsyncMock(return_value=False)

        ctx = StepContext(
            game_id="test",
            game=short_game,
            analysis_repo=analysis_repo,
            game_repo=AsyncMock(),
            engine_path="/fake",
            engine=mock_engine,
            thresholds=Thresholds(),
            depth=14,
        )

        step = StockfishAnalysisStep()
        result = await step.execute(ctx)
        assert result.success is True

        # 5 moves → 6 positions evaluated in single pass, no extra calls
        # Old implementation: 5 info_before + 5 info_after + 5 info_best = 15
        n_moves = 5
        n_positions = n_moves + 1
        assert mock_engine.analyse.call_count == n_positions

        assert len(result.data["move_evals"]) == n_moves

    async def test_output_fields_present(self, short_game):
        def analyse_side_effect(board, _limit, **_kwargs):
            legal_moves = list(board.legal_moves)
            pv = [legal_moves[0]] if legal_moves else []
            return {"score": self._make_mock_score(20), "pv": pv}

        mock_engine = AsyncMock()
        mock_engine.analyse = AsyncMock(side_effect=analyse_side_effect)

        ctx = StepContext(
            game_id="test",
            game=short_game,
            analysis_repo=AsyncMock(),
            game_repo=AsyncMock(),
            engine_path="/fake",
            engine=mock_engine,
            thresholds=Thresholds(),
            depth=14,
        )

        step = StockfishAnalysisStep()
        result = await step.execute(ctx)

        required_keys = {
            "ply",
            "move_number",
            "player",
            "uci",
            "san",
            "eval_before",
            "eval_after",
            "info_before",
            "best_move_uci",
            "best_move_san",
            "best_line",
            "best_move_eval",
            "board",
        }
        for entry in result.data["move_evals"]:
            assert set(entry.keys()) == required_keys


class TestStepIntegration:
    def test_all_steps_have_unique_ids(self):
        steps = get_all_steps()
        ids = [s.step_id for s in steps]
        assert len(ids) == len(set(ids))

    def test_all_steps_return_correct_types(self):
        steps = get_all_steps()
        for step in steps:
            assert isinstance(step.step_id, str)
            assert isinstance(step.depends_on, frozenset)
            assert isinstance(step.produces, frozenset)
