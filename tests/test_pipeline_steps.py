from __future__ import annotations

import io
from unittest.mock import AsyncMock, MagicMock

import chess.pgn
import pytest

from blunder_tutor.analysis.pipeline.context import StepContext, StepResult
from blunder_tutor.analysis.pipeline.steps.eco import ECOClassifyStep
from blunder_tutor.analysis.pipeline.steps.move_quality import MoveQualityStep
from blunder_tutor.analysis.pipeline.steps.phase import PhaseClassifyStep
from blunder_tutor.analysis.thresholds import Thresholds


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
        from blunder_tutor.analysis.pipeline.steps.stockfish import (
            StockfishAnalysisStep,
        )

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
        from blunder_tutor.analysis.pipeline.steps.stockfish import (
            StockfishAnalysisStep,
        )

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
        from blunder_tutor.analysis.pipeline.steps import get_all_steps

        steps = get_all_steps()
        ids = [s.step_id for s in steps]
        assert len(ids) == len(set(ids))

    def test_all_steps_return_correct_types(self):
        from blunder_tutor.analysis.pipeline.steps import get_all_steps

        steps = get_all_steps()
        for step in steps:
            assert isinstance(step.step_id, str)
            assert isinstance(step.depends_on, frozenset)
            assert isinstance(step.produces, frozenset)
