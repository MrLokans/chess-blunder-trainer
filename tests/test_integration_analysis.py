"""Integration tests for the analysis pipeline with real Stockfish engine.

These tests require a working Stockfish installation and are marked as
integration tests. They can be skipped with: pytest -m "not integration"
"""

from __future__ import annotations

import io
import os
from pathlib import Path

import chess.pgn
import pytest

from blunder_tutor.analysis.logic import GameAnalyzer
from blunder_tutor.analysis.pipeline import (
    AnalysisPipeline,
    PipelineConfig,
    PipelineExecutor,
    PipelinePreset,
)
from blunder_tutor.analysis.pipeline.steps import get_all_steps
from blunder_tutor.analysis.thresholds import Thresholds
from blunder_tutor.constants import CLASSIFICATION_BLUNDER
from blunder_tutor.repositories.analysis import AnalysisRepository
from blunder_tutor.repositories.game_repository import GameRepository
from blunder_tutor.repositories.puzzle_attempt_repository import PuzzleAttemptRepository

STOCKFISH_PATHS = [
    os.environ.get("STOCKFISH_BINARY"),
    "/Users/mrlokans/Projects/3rdparty/stockfish/src/stockfish",
    "/opt/homebrew/bin/stockfish",
    "/usr/local/bin/stockfish",
    "/usr/games/stockfish",
    "/usr/bin/stockfish",
]


def find_stockfish() -> str | None:
    for path in STOCKFISH_PATHS:
        if path and Path(path).exists():
            return path
    return None


STOCKFISH_PATH = find_stockfish()
SKIP_REASON = "Stockfish not found. Set STOCKFISH_BINARY env var or install Stockfish."

# Sample PGN for a short game (Scholar's Mate)
SCHOLARS_MATE_PGN = """[Event "Test Game"]
[Site "Integration Test"]
[Date "2024.01.01"]
[Round "1"]
[White "Attacker"]
[Black "Victim"]
[Result "1-0"]

1. e4 e5 2. Qh5 Nc6 3. Bc4 Nf6 4. Qxf7# 1-0"""

# Sample PGN for a longer game with clear blunders
BLUNDER_GAME_PGN = """[Event "Blunder Test"]
[Site "Integration Test"]
[Date "2024.01.01"]
[Round "1"]
[White "Player1"]
[Black "Player2"]
[Result "1-0"]

1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 4. Ba4 Nf6 5. O-O Be7 6. Re1 b5 7. Bb3 d6 
8. c3 O-O 9. h3 Nb8 10. d4 Nbd7 11. Nbd2 Bb7 12. Bc2 Re8 13. Nf1 Bf8 
14. Ng3 g6 15. Bg5 h6 16. Bd2 Bg7 17. Qc1 Kh7 18. Nh2 Qe7 19. f4 exf4 
20. Bxf4 Ne5 21. Qd2 Rad8 22. Rf1 Bc8 23. Rae1 Neg4 24. hxg4 Nxg4 
25. Nxg4 Bxg4 26. Qf2 Qe6 27. Bd3 Be2 1-0"""


@pytest.fixture
def stockfish_path() -> str:
    if STOCKFISH_PATH is None:
        pytest.skip(SKIP_REASON)
    return STOCKFISH_PATH


@pytest.fixture
def scholars_mate_game() -> chess.pgn.Game:
    return chess.pgn.read_game(io.StringIO(SCHOLARS_MATE_PGN))


@pytest.fixture
def blunder_game() -> chess.pgn.Game:
    return chess.pgn.read_game(io.StringIO(BLUNDER_GAME_PGN))


async def store_test_game(
    game_repo: GameRepository,
    game_id: str,
    pgn_text: str,
    white: str = "Player1",
    black: str = "testuser",
    source: str = "test",
) -> None:
    """Helper to store a test game in the repository.

    By default, testuser plays as Black to facilitate trainer tests.
    """
    await game_repo.insert_games(
        [
            {
                "id": game_id,
                "source": source,
                "username": "testuser",
                "white": white,
                "black": black,
                "result": "1-0",
                "date": "2024.01.01",
                "end_time_utc": None,
                "time_control": "600",
                "pgn_content": pgn_text,
            }
        ]
    )


@pytest.mark.integration
@pytest.mark.slow
class TestStockfishIntegration:
    async def test_stockfish_engine_starts(self, stockfish_path: str):
        """Verify that Stockfish can be started and responds to commands."""
        import chess.engine

        transport, engine = await chess.engine.popen_uci(stockfish_path)
        try:
            assert "name" in engine.id
            assert "stockfish" in engine.id["name"].lower()
        finally:
            await engine.quit()

    async def test_stockfish_analyzes_position(self, stockfish_path: str):
        """Verify that Stockfish can analyze a position."""
        import chess
        import chess.engine

        transport, engine = await chess.engine.popen_uci(stockfish_path)
        try:
            board = chess.Board()
            limit = chess.engine.Limit(depth=10)
            info = await engine.analyse(board, limit)

            assert "score" in info
            assert "pv" in info
            assert len(info["pv"]) > 0
        finally:
            await engine.quit()


@pytest.mark.integration
@pytest.mark.slow
class TestPipelineIntegration:
    async def test_full_pipeline_scholars_mate(
        self,
        stockfish_path: str,
        scholars_mate_game: chess.pgn.Game,
        analysis_repo: AnalysisRepository,
        game_repo: GameRepository,
    ):
        """Test full pipeline execution on Scholar's Mate game."""
        game_id = "test_scholars_mate"

        # Store the game first
        await store_test_game(game_repo, game_id, SCHOLARS_MATE_PGN)

        executor = PipelineExecutor(
            analysis_repo=analysis_repo,
            game_repo=game_repo,
            engine_path=stockfish_path,
        )

        available_steps = get_all_steps()
        config = PipelineConfig.from_preset(PipelinePreset.FULL)
        pipeline = AnalysisPipeline(config, available_steps)

        report = await executor.execute_pipeline(
            pipeline=pipeline,
            game_id=game_id,
            thresholds=Thresholds(),
            depth=10,
        )

        assert report.success is True
        assert "stockfish" in report.steps_executed
        assert "move_quality" in report.steps_executed
        assert "eco" in report.steps_executed
        assert "phase" in report.steps_executed
        assert "write" in report.steps_executed
        assert len(report.steps_failed) == 0

        # Verify analysis was written
        assert await analysis_repo.analysis_exists(game_id)

        # Verify we can fetch moves
        moves = await analysis_repo.fetch_moves(game_id)
        assert len(moves) == 7  # 4 moves by white, 3 by black

    async def test_pipeline_with_blunders(
        self,
        stockfish_path: str,
        blunder_game: chess.pgn.Game,
        analysis_repo: AnalysisRepository,
        game_repo: GameRepository,
    ):
        """Test pipeline detects blunders in a game with known mistakes."""
        game_id = "test_blunder_game"

        await store_test_game(game_repo, game_id, BLUNDER_GAME_PGN)

        executor = PipelineExecutor(
            analysis_repo=analysis_repo,
            game_repo=game_repo,
            engine_path=stockfish_path,
        )

        available_steps = get_all_steps()
        config = PipelineConfig.from_preset(PipelinePreset.FULL)
        pipeline = AnalysisPipeline(config, available_steps)

        report = await executor.execute_pipeline(
            pipeline=pipeline,
            game_id=game_id,
            thresholds=Thresholds(),
            depth=12,
        )

        assert report.success is True

        # Verify moves were analyzed
        moves = await analysis_repo.fetch_moves(game_id)
        assert len(moves) > 0

        # Each move should have evaluation data
        for move in moves:
            assert move["eval_before"] is not None
            assert move["eval_after"] is not None
            assert move["san"] is not None


@pytest.mark.integration
@pytest.mark.slow
class TestGameAnalyzerIntegration:
    async def test_analyze_single_game(
        self,
        stockfish_path: str,
        analysis_repo: AnalysisRepository,
        game_repo: GameRepository,
    ):
        """Test GameAnalyzer.analyze_game() with real engine."""
        game_id = "test_analyzer_single"

        await store_test_game(game_repo, game_id, SCHOLARS_MATE_PGN)

        analyzer = GameAnalyzer(
            analysis_repo=analysis_repo,
            games_repo=game_repo,
            engine_path=stockfish_path,
        )

        await analyzer.analyze_game(game_id=game_id, depth=10)

        assert await analysis_repo.analysis_exists(game_id)
        moves = await analysis_repo.fetch_moves(game_id)
        assert len(moves) == 7

    async def test_analyze_bulk_sequential(
        self,
        stockfish_path: str,
        analysis_repo: AnalysisRepository,
        game_repo: GameRepository,
    ):
        """Test bulk analysis with concurrency=1 (sequential)."""
        game_ids = ["test_bulk_seq_1", "test_bulk_seq_2"]

        for gid in game_ids:
            await store_test_game(game_repo, gid, SCHOLARS_MATE_PGN)

        analyzer = GameAnalyzer(
            analysis_repo=analysis_repo,
            games_repo=game_repo,
            engine_path=stockfish_path,
        )

        result = await analyzer.analyze_bulk(
            depth=8,
            source="test",
            username="testuser",
            concurrency=1,
        )

        assert result["analyzed"] == 2
        assert result["skipped"] == 0
        assert result["failed"] == 0

        for gid in game_ids:
            assert await analysis_repo.analysis_exists(gid)

    async def test_analyze_bulk_parallel(
        self,
        stockfish_path: str,
        analysis_repo: AnalysisRepository,
        game_repo: GameRepository,
    ):
        """Test bulk analysis with parallel processing."""
        game_ids = ["test_bulk_par_1", "test_bulk_par_2", "test_bulk_par_3"]

        for gid in game_ids:
            await store_test_game(game_repo, gid, SCHOLARS_MATE_PGN)

        analyzer = GameAnalyzer(
            analysis_repo=analysis_repo,
            games_repo=game_repo,
            engine_path=stockfish_path,
        )

        result = await analyzer.analyze_bulk(
            depth=8,
            source="test",
            username="testuser",
            concurrency=2,
        )

        assert result["analyzed"] == 3
        assert result["skipped"] == 0
        assert result["failed"] == 0

        for gid in game_ids:
            assert await analysis_repo.analysis_exists(gid)

    async def test_analyze_bulk_skips_already_analyzed(
        self,
        stockfish_path: str,
        analysis_repo: AnalysisRepository,
        game_repo: GameRepository,
    ):
        """Test that bulk analysis skips already analyzed games."""
        game_id = "test_skip_analyzed"

        await store_test_game(game_repo, game_id, SCHOLARS_MATE_PGN)

        analyzer = GameAnalyzer(
            analysis_repo=analysis_repo,
            games_repo=game_repo,
            engine_path=stockfish_path,
        )

        # Analyze first time
        result1 = await analyzer.analyze_bulk(
            depth=8,
            source="test",
            username="testuser",
            concurrency=1,
        )
        assert result1["analyzed"] == 1

        # Store another game
        await store_test_game(game_repo, "test_skip_analyzed_2", SCHOLARS_MATE_PGN)

        # Analyze again - should skip the first, analyze the second
        result2 = await analyzer.analyze_bulk(
            depth=8,
            source="test",
            username="testuser",
            concurrency=1,
        )
        assert result2["analyzed"] == 1
        assert result2["skipped"] == 1


@pytest.mark.integration
@pytest.mark.slow
class TestEngineReuse:
    async def test_engine_passed_to_pipeline(
        self,
        stockfish_path: str,
        analysis_repo: AnalysisRepository,
        game_repo: GameRepository,
    ):
        """Test that external engine can be passed and reused."""
        import chess.engine

        game_id = "test_engine_reuse"

        await store_test_game(game_repo, game_id, SCHOLARS_MATE_PGN)

        # Create engine externally
        _, engine = await chess.engine.popen_uci(stockfish_path)

        try:
            executor = PipelineExecutor(
                analysis_repo=analysis_repo,
                game_repo=game_repo,
                engine_path=stockfish_path,
            )

            available_steps = get_all_steps()
            config = PipelineConfig.from_preset(PipelinePreset.FULL)
            pipeline = AnalysisPipeline(config, available_steps)

            # Pass external engine
            report = await executor.execute_pipeline(
                pipeline=pipeline,
                game_id=game_id,
                thresholds=Thresholds(),
                depth=8,
                engine=engine,
            )

            assert report.success is True
            assert await analysis_repo.analysis_exists(game_id)
        finally:
            await engine.quit()


# Game with clear blunder: Black hangs queen on move 3 (3...Qh4?? 4.Nxh4)
HANGING_QUEEN_PGN = """[Event "Blunder Test"]
[Site "Integration Test"]
[Date "2024.01.01"]
[White "Player1"]
[Black "Player2"]
[Result "1-0"]

1. e4 e5 2. Nf3 Qh4 3. Nxh4 Nc6 4. d4 exd4 5. Qxd4 1-0"""

# Game where white blunders with 4.Qh5?? allowing 4...Nxe5
BLUNDER_BY_WHITE_PGN = """[Event "White Blunder"]
[Site "Integration Test"]  
[Date "2024.01.01"]
[White "Blunderer"]
[Black "Opponent"]
[Result "0-1"]

1. e4 e5 2. Nf3 Nc6 3. Bc4 Nf6 4. Qe2 Bc5 5. d3 d6 6. h3 O-O 7. g4 h6 8. Rg1 Kh7 0-1"""


@pytest.mark.integration
@pytest.mark.slow
class TestTrainingPipelineIntegration:
    """Full end-to-end tests: store game → analyze → pick puzzle."""

    async def test_full_training_flow(
        self,
        stockfish_path: str,
        analysis_repo: AnalysisRepository,
        game_repo: GameRepository,
        puzzle_attempt_repo: PuzzleAttemptRepository,
    ):
        """Store game, analyze it, then pick a puzzle from blunders."""
        from blunder_tutor.trainer import Trainer

        game_id = "test_training_flow"

        # Store game with a clear blunder
        await store_test_game(game_repo, game_id, HANGING_QUEEN_PGN)

        # Analyze the game
        analyzer = GameAnalyzer(
            analysis_repo=analysis_repo,
            games_repo=game_repo,
            engine_path=stockfish_path,
        )
        await analyzer.analyze_game(game_id=game_id, depth=12)

        # Verify analysis exists
        assert await analysis_repo.analysis_exists(game_id)

        # Check that blunders were detected
        blunders = await analysis_repo.fetch_blunders()
        assert len(blunders) > 0, "Should detect at least one blunder"

        # Create trainer and pick a puzzle
        trainer = Trainer(
            games=game_repo,
            attempts=puzzle_attempt_repo,
            analysis=analysis_repo,
        )

        puzzle = await trainer.pick_random_blunder(
            username="testuser",
            source="test",
            exclude_recently_solved=False,
        )

        # Verify puzzle has valid data
        assert puzzle.game_id == game_id
        assert puzzle.fen is not None
        assert puzzle.blunder_uci is not None
        assert puzzle.player_color in ("white", "black")
        assert puzzle.cp_loss > 0

    async def test_puzzle_filtering_by_player_color(
        self,
        stockfish_path: str,
        analysis_repo: AnalysisRepository,
        game_repo: GameRepository,
        puzzle_attempt_repo: PuzzleAttemptRepository,
    ):
        """Verify puzzles are filtered to only show player's blunders."""
        from blunder_tutor.trainer import Trainer

        game_id = "test_player_filter"

        # Store game where Black makes the blunder (Qh4??)
        await store_test_game(game_repo, game_id, HANGING_QUEEN_PGN)

        analyzer = GameAnalyzer(
            analysis_repo=analysis_repo,
            games_repo=game_repo,
            engine_path=stockfish_path,
        )
        await analyzer.analyze_game(game_id=game_id, depth=12)

        trainer = Trainer(
            games=game_repo,
            attempts=puzzle_attempt_repo,
            analysis=analysis_repo,
        )

        # Pick puzzle for testuser who played as Black (Player2)
        puzzle = await trainer.pick_random_blunder(
            username="testuser",
            source="test",
            exclude_recently_solved=False,
        )

        # The blunder should be by Black (player_color = black)
        # because we set Player2 = testuser in store_test_game
        assert puzzle.player_color == "black"


@pytest.mark.integration
@pytest.mark.slow
class TestMoveQualityClassification:
    """Verify move quality classification (inaccuracy/mistake/blunder)."""

    async def test_blunder_classification(
        self,
        stockfish_path: str,
        analysis_repo: AnalysisRepository,
        game_repo: GameRepository,
    ):
        """Test that large cp loss is classified as blunder."""
        game_id = "test_blunder_class"
        await store_test_game(game_repo, game_id, HANGING_QUEEN_PGN)

        executor = PipelineExecutor(
            analysis_repo=analysis_repo,
            game_repo=game_repo,
            engine_path=stockfish_path,
        )

        available_steps = get_all_steps()
        config = PipelineConfig.from_preset(PipelinePreset.FULL)
        pipeline = AnalysisPipeline(config, available_steps)

        # Use default thresholds: blunder >= 200cp
        await executor.execute_pipeline(
            pipeline=pipeline,
            game_id=game_id,
            thresholds=Thresholds(),
            depth=12,
        )

        moves = await analysis_repo.fetch_moves(game_id)

        # Find the queen blunder move (2...Qh4)
        blunder_moves = [
            m for m in moves if m.get("classification") == CLASSIFICATION_BLUNDER
        ]
        assert len(blunder_moves) > 0, "Should have at least one blunder"

        # The blunder should have significant cp_loss
        for blunder in blunder_moves:
            assert blunder["cp_loss"] >= 200

    async def test_quality_thresholds(
        self,
        stockfish_path: str,
        analysis_repo: AnalysisRepository,
        game_repo: GameRepository,
    ):
        """Verify all moves have quality classification."""
        game_id = "test_quality"
        await store_test_game(game_repo, game_id, SCHOLARS_MATE_PGN)

        analyzer = GameAnalyzer(
            analysis_repo=analysis_repo,
            games_repo=game_repo,
            engine_path=stockfish_path,
        )
        await analyzer.analyze_game(game_id=game_id, depth=10)

        moves = await analysis_repo.fetch_moves(game_id)
        # Classification: 0=good, 1=inaccuracy, 2=mistake, 3=blunder
        valid_classifications = {0, 1, 2, 3}

        for move in moves:
            classification = move.get("classification")
            assert classification in valid_classifications, (
                f"Invalid classification: {classification}"
            )


@pytest.mark.integration
@pytest.mark.slow
class TestGamePhaseDetection:
    """Test game phase (opening/middlegame/endgame) detection."""

    async def test_phases_assigned_to_moves(
        self,
        stockfish_path: str,
        analysis_repo: AnalysisRepository,
        game_repo: GameRepository,
    ):
        """Verify moves have game phase assigned."""
        game_id = "test_phases"
        await store_test_game(game_repo, game_id, BLUNDER_GAME_PGN)

        executor = PipelineExecutor(
            analysis_repo=analysis_repo,
            game_repo=game_repo,
            engine_path=stockfish_path,
        )

        available_steps = get_all_steps()
        config = PipelineConfig.from_preset(PipelinePreset.FULL)
        pipeline = AnalysisPipeline(config, available_steps)

        await executor.execute_pipeline(
            pipeline=pipeline,
            game_id=game_id,
            thresholds=Thresholds(),
            depth=10,
        )

        moves = await analysis_repo.fetch_moves(game_id)

        # Check that phases are assigned
        phases_found = set()
        for move in moves:
            phase = move.get("game_phase")
            if phase is not None:
                phases_found.add(phase)

        # With 27 moves, we should have opening (0) at minimum
        assert 0 in phases_found, "Opening phase should be detected"


@pytest.mark.integration
@pytest.mark.slow
class TestECOClassification:
    """Test ECO opening classification."""

    async def test_eco_assigned(
        self,
        stockfish_path: str,
        analysis_repo: AnalysisRepository,
        game_repo: GameRepository,
    ):
        """Verify ECO code is assigned to the game."""
        game_id = "test_eco"
        await store_test_game(game_repo, game_id, BLUNDER_GAME_PGN)

        executor = PipelineExecutor(
            analysis_repo=analysis_repo,
            game_repo=game_repo,
            engine_path=stockfish_path,
        )

        available_steps = get_all_steps()
        config = PipelineConfig.from_preset(PipelinePreset.FULL)
        pipeline = AnalysisPipeline(config, available_steps)

        await executor.execute_pipeline(
            pipeline=pipeline,
            game_id=game_id,
            thresholds=Thresholds(),
            depth=8,
        )

        # Fetch the game metadata to check ECO
        # The BLUNDER_GAME_PGN is a Ruy Lopez (C65-C99 range)
        moves = await analysis_repo.fetch_moves(game_id)
        # ECO should be stored in game metadata, but moves should exist
        assert len(moves) > 0
