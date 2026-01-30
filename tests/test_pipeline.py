from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import chess.pgn
import pytest

from blunder_tutor.analysis.pipeline import (
    AnalysisPipeline,
    PipelineConfig,
    PipelineExecutor,
    PipelinePreset,
)
from blunder_tutor.analysis.pipeline.context import StepContext, StepResult
from blunder_tutor.analysis.pipeline.steps import get_all_steps
from blunder_tutor.analysis.pipeline.steps.base import AnalysisStep
from blunder_tutor.analysis.thresholds import Thresholds


class DummyStep(AnalysisStep):
    def __init__(self, step_id: str, depends: frozenset[str] | None = None):
        self._step_id = step_id
        self._depends = depends or frozenset()

    @property
    def step_id(self) -> str:
        return self._step_id

    @property
    def depends_on(self) -> frozenset[str]:
        return self._depends

    async def execute(self, ctx: StepContext) -> StepResult:
        return StepResult(step_id=self.step_id, success=True)


class TestPipelineConfig:
    def test_from_preset_full(self):
        config = PipelineConfig.from_preset(PipelinePreset.FULL)
        assert "eco" in config.steps
        assert "stockfish" in config.steps
        assert "move_quality" in config.steps
        assert "phase" in config.steps
        assert "write" in config.steps
        assert config.force_rerun is False

    def test_from_preset_fast(self):
        config = PipelineConfig.from_preset(PipelinePreset.FAST)
        assert config.steps == ["eco", "phase"]

    def test_from_preset_with_force_rerun(self):
        config = PipelineConfig.from_preset(PipelinePreset.FULL, force_rerun=True)
        assert config.force_rerun is True


class TestAnalysisPipeline:
    def test_validates_unknown_step(self):
        steps = [DummyStep("a"), DummyStep("b")]
        config = PipelineConfig(steps=["a", "unknown"])

        with pytest.raises(ValueError, match="Unknown step 'unknown'"):
            AnalysisPipeline(config, steps)

    def test_get_ordered_steps_simple(self):
        steps = [DummyStep("a"), DummyStep("b"), DummyStep("c")]
        config = PipelineConfig(steps=["a", "b"])
        pipeline = AnalysisPipeline(config, steps)

        ordered = pipeline.get_ordered_steps()
        step_ids = [s.step_id for s in ordered]
        assert set(step_ids) == {"a", "b"}

    def test_get_ordered_steps_with_dependencies(self):
        step_a = DummyStep("a")
        step_b = DummyStep("b", frozenset({"a"}))
        step_c = DummyStep("c", frozenset({"b"}))
        steps = [step_a, step_b, step_c]

        config = PipelineConfig(steps=["c", "b", "a"])
        pipeline = AnalysisPipeline(config, steps)

        ordered = pipeline.get_ordered_steps()
        step_ids = [s.step_id for s in ordered]

        # a must come before b, b must come before c
        assert step_ids.index("a") < step_ids.index("b")
        assert step_ids.index("b") < step_ids.index("c")

    def test_from_preset(self):
        available_steps = get_all_steps()
        pipeline = AnalysisPipeline.from_preset(PipelinePreset.FAST, available_steps)
        ordered = pipeline.get_ordered_steps()
        step_ids = [s.step_id for s in ordered]
        assert "eco" in step_ids
        assert "phase" in step_ids


class TestPipelineExecutor:
    @pytest.fixture
    def mock_repos(self):
        analysis_repo = AsyncMock()
        game_repo = AsyncMock()

        analysis_repo.is_step_completed = AsyncMock(return_value=False)
        analysis_repo.mark_step_completed = AsyncMock()
        analysis_repo.get_game_eco = AsyncMock(
            return_value={"eco_code": None, "eco_name": None}
        )
        analysis_repo.update_game_eco = AsyncMock()

        return analysis_repo, game_repo

    @pytest.fixture
    def sample_game(self):
        import io

        pgn_text = """[Event "Test"]
[Site "?"]
[Date "2024.01.01"]
[Round "1"]
[White "Player1"]
[Black "Player2"]
[Result "1-0"]

1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 1-0"""
        return chess.pgn.read_game(io.StringIO(pgn_text))

    async def test_execute_pipeline_basic(self, mock_repos, sample_game):
        analysis_repo, game_repo = mock_repos
        game_repo.load_game = AsyncMock(return_value=sample_game)

        step = DummyStep("test_step")
        config = PipelineConfig(steps=["test_step"])
        pipeline = AnalysisPipeline(config, [step])

        executor = PipelineExecutor(
            analysis_repo=analysis_repo,
            game_repo=game_repo,
            engine_path="/path/to/engine",
        )

        report = await executor.execute_pipeline(
            pipeline=pipeline,
            game_id="test_game_id",
        )

        assert report.success is True
        assert "test_step" in report.steps_executed
        analysis_repo.mark_step_completed.assert_called_once()

    async def test_execute_pipeline_skips_completed_steps(
        self, mock_repos, sample_game
    ):
        analysis_repo, game_repo = mock_repos
        game_repo.load_game = AsyncMock(return_value=sample_game)
        analysis_repo.is_step_completed = AsyncMock(return_value=True)

        step = DummyStep("test_step")
        config = PipelineConfig(steps=["test_step"])
        pipeline = AnalysisPipeline(config, [step])

        executor = PipelineExecutor(
            analysis_repo=analysis_repo,
            game_repo=game_repo,
            engine_path="/path/to/engine",
        )

        report = await executor.execute_pipeline(
            pipeline=pipeline,
            game_id="test_game_id",
        )

        assert report.success is True
        assert "test_step" in report.steps_skipped
        assert "test_step" not in report.steps_executed

    async def test_execute_pipeline_force_rerun(self, mock_repos, sample_game):
        analysis_repo, game_repo = mock_repos
        game_repo.load_game = AsyncMock(return_value=sample_game)
        analysis_repo.is_step_completed = AsyncMock(return_value=True)

        step = DummyStep("test_step")
        config = PipelineConfig(steps=["test_step"], force_rerun=True)
        pipeline = AnalysisPipeline(config, [step])

        executor = PipelineExecutor(
            analysis_repo=analysis_repo,
            game_repo=game_repo,
            engine_path="/path/to/engine",
        )

        report = await executor.execute_pipeline(
            pipeline=pipeline,
            game_id="test_game_id",
        )

        assert report.success is True
        assert "test_step" in report.steps_executed
        assert "test_step" not in report.steps_skipped


class TestStepContext:
    def test_add_and_get_step_result(self):
        ctx = StepContext(
            game_id="test",
            game=MagicMock(),
            analysis_repo=MagicMock(),
            game_repo=MagicMock(),
            engine_path="/path/to/engine",
            thresholds=Thresholds(),
        )

        result = StepResult(step_id="test_step", success=True, data={"key": "value"})
        ctx.add_step_result(result)

        retrieved = ctx.get_step_result("test_step")
        assert retrieved is not None
        assert retrieved.success is True
        assert retrieved.data["key"] == "value"

    def test_get_missing_step_result(self):
        ctx = StepContext(
            game_id="test",
            game=MagicMock(),
            analysis_repo=MagicMock(),
            game_repo=MagicMock(),
            engine_path="/path/to/engine",
            thresholds=Thresholds(),
        )

        result = ctx.get_step_result("nonexistent")
        assert result is None
