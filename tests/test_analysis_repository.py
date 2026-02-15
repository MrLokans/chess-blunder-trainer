"""Tests for AnalysisRepository."""

from __future__ import annotations

from blunder_tutor.repositories.analysis import AnalysisRepository
from blunder_tutor.repositories.game_repository import GameRepository
from blunder_tutor.utils.time_control import GAME_TYPE_FROM_STRING


def _make_move(ply: int, **overrides: object) -> dict[str, object]:
    defaults = {
        "ply": ply,
        "move_number": (ply + 1) // 2,
        "player": "white" if ply % 2 == 1 else "black",
        "uci": "e2e4",
        "san": "e4",
        "eval_before": 0,
        "eval_after": 0,
        "delta": 0,
        "cp_loss": 0,
        "classification": 0,
    }
    defaults.update(overrides)
    return defaults


def _blunder_move(ply: int, **overrides: object) -> dict[str, object]:
    return _make_move(
        ply,
        eval_before=50,
        eval_after=-200,
        delta=-250,
        cp_loss=250,
        classification=3,
        best_move_uci="d2d4",
        best_move_san="d4",
        **overrides,
    )


THRESHOLDS = {"inaccuracy": 50, "mistake": 100, "blunder": 200}


async def _write_game(repo: AnalysisRepository, game_id: str = "g1", moves=None, **kw):
    defaults = {
        "game_id": game_id,
        "pgn_path": "",
        "analyzed_at": "2025-01-01",
        "engine_path": "",
        "depth": 20,
        "time_limit": 1.0,
        "thresholds": THRESHOLDS,
        "moves": moves or [_make_move(1)],
    }
    defaults.update(kw)
    await repo.write_analysis(**defaults)


class TestFetchBlundersWithPhaseFilter:
    async def test_no_filter_returns_all(self, analysis_repo: AnalysisRepository):
        await _write_game(
            analysis_repo,
            moves=[
                _blunder_move(1, game_phase=0),
                _blunder_move(3, game_phase=1),
                _blunder_move(5, game_phase=2),
            ],
        )
        blunders = await analysis_repo.fetch_blunders()
        assert len(blunders) == 3

    async def test_phase_filter(self, analysis_repo: AnalysisRepository):
        await _write_game(
            analysis_repo,
            moves=[
                _blunder_move(1, game_phase=0),
                _blunder_move(3, game_phase=1),
                _blunder_move(5, game_phase=2),
            ],
        )
        blunders = await analysis_repo.fetch_blunders(game_phases=[0])
        assert len(blunders) == 1
        assert blunders[0]["game_phase"] == 0

    async def test_multiple_phases(self, analysis_repo: AnalysisRepository):
        await _write_game(
            analysis_repo,
            moves=[
                _blunder_move(1, game_phase=0),
                _blunder_move(3, game_phase=1),
                _blunder_move(5, game_phase=2),
            ],
        )
        blunders = await analysis_repo.fetch_blunders(game_phases=[0, 2])
        assert len(blunders) == 2


class TestGetMoveAnalysis:
    async def test_existing_move(self, analysis_repo: AnalysisRepository):
        await _write_game(
            analysis_repo,
            moves=[
                _blunder_move(
                    5, tactical_pattern=1, tactical_reason="fork", difficulty=45
                ),
            ],
        )
        result = await analysis_repo.get_move_analysis("g1", 5)
        assert result is not None
        assert result["ply"] == 5
        assert result["cp_loss"] == 250
        assert result["tactical_pattern"] == 1
        assert result["difficulty"] == 45

    async def test_nonexistent(self, analysis_repo: AnalysisRepository):
        result = await analysis_repo.get_move_analysis("g1", 99)
        assert result is None


class TestStepCompletion:
    async def test_mark_and_check(self, analysis_repo: AnalysisRepository):
        await _write_game(analysis_repo)
        assert not await analysis_repo.is_step_completed("g1", "eco")
        await analysis_repo.mark_step_completed("g1", "eco")
        assert await analysis_repo.is_step_completed("g1", "eco")

    async def test_get_completed_steps(self, analysis_repo: AnalysisRepository):
        await _write_game(analysis_repo)
        await analysis_repo.mark_step_completed("g1", "eco")
        await analysis_repo.mark_step_completed("g1", "phase")
        steps = await analysis_repo.get_completed_steps("g1")
        assert steps == {"eco", "phase"}

    async def test_clear_step_status(self, analysis_repo: AnalysisRepository):
        await _write_game(analysis_repo)
        await analysis_repo.mark_step_completed("g1", "eco")
        await analysis_repo.clear_step_status("g1")
        assert not await analysis_repo.is_step_completed("g1", "eco")
        assert await analysis_repo.get_completed_steps("g1") == set()


class TestPhaseBackfill:
    async def test_get_game_ids_missing_phase(self, analysis_repo: AnalysisRepository):
        await _write_game(analysis_repo, game_id="g1", moves=[_make_move(1)])
        await _write_game(
            analysis_repo, game_id="g2", moves=[_make_move(1, game_phase=1)]
        )
        ids = await analysis_repo.get_game_ids_missing_phase()
        assert "g1" in ids
        assert "g2" not in ids

    async def test_update_move_phase(self, analysis_repo: AnalysisRepository):
        await _write_game(analysis_repo, moves=[_make_move(1)])
        await analysis_repo.update_move_phase("g1", 1, 2)
        result = await analysis_repo.get_move_analysis("g1", 1)
        assert result["game_phase"] == 2

    async def test_update_moves_phases_batch(self, analysis_repo: AnalysisRepository):
        await _write_game(analysis_repo, moves=[_make_move(1), _make_move(2)])
        await analysis_repo.update_moves_phases_batch(
            [
                (0, "g1", 1),
                (1, "g1", 2),
            ]
        )
        assert (await analysis_repo.get_move_analysis("g1", 1))["game_phase"] == 0
        assert (await analysis_repo.get_move_analysis("g1", 2))["game_phase"] == 1


class TestEcoBackfill:
    async def test_get_game_ids_missing_eco(self, analysis_repo: AnalysisRepository):
        await _write_game(analysis_repo, game_id="g1")
        await _write_game(
            analysis_repo, game_id="g2", eco_code="B00", eco_name="Sicilian"
        )
        ids = await analysis_repo.get_game_ids_missing_eco()
        assert "g1" in ids
        assert "g2" not in ids

    async def test_update_and_get_game_eco(self, analysis_repo: AnalysisRepository):
        await _write_game(analysis_repo)
        await analysis_repo.update_game_eco("g1", "C00", "French Defense")
        eco = await analysis_repo.get_game_eco("g1")
        assert eco["eco_code"] == "C00"
        assert eco["eco_name"] == "French Defense"

    async def test_get_game_eco_not_found(self, analysis_repo: AnalysisRepository):
        eco = await analysis_repo.get_game_eco("nonexistent")
        assert eco["eco_code"] is None

    async def test_eco_step_excludes_completed(self, analysis_repo: AnalysisRepository):
        await _write_game(analysis_repo, game_id="g1")
        await analysis_repo.mark_step_completed("g1", "eco")
        ids = await analysis_repo.get_game_ids_missing_eco()
        assert "g1" not in ids


class TestFetchMovesForPhaseBackfill:
    async def test_returns_moves_without_phase(self, analysis_repo: AnalysisRepository):
        await _write_game(
            analysis_repo,
            moves=[
                _make_move(1),
                _make_move(2, game_phase=1),
                _make_move(3),
            ],
        )
        moves = await analysis_repo.fetch_moves_for_phase_backfill("g1")
        assert len(moves) == 2
        assert moves[0]["ply"] == 1
        assert moves[1]["ply"] == 3


class TestUpdateMovesTacticsBatch:
    async def test_batch_update(self, analysis_repo: AnalysisRepository):
        await _write_game(
            analysis_repo,
            moves=[
                _blunder_move(1),
                _blunder_move(3),
            ],
        )
        await analysis_repo.update_moves_tactics_batch(
            [
                (1, "fork", "g1", 1),
                (2, "pin", "g1", 3),
            ]
        )
        r1 = await analysis_repo.get_move_analysis("g1", 1)
        r3 = await analysis_repo.get_move_analysis("g1", 3)
        assert r1["tactical_pattern"] == 1
        assert r3["tactical_pattern"] == 2


class TestFetchBlundersWithTactics:
    async def _seed(self, analysis_repo, game_repo):
        await game_repo.insert_games(
            [
                {
                    "id": "g1",
                    "source": "lichess",
                    "username": "testuser",
                    "white": "testuser",
                    "black": "opponent",
                    "result": "1-0",
                    "date": "2024.01.10",
                    "end_time_utc": "2024-01-10T12:00:00",
                    "time_control": "300+0",
                    "pgn_content": '[Event "Test"]\n1. e4 e5 1-0',
                }
            ]
        )
        await _write_game(
            analysis_repo,
            game_id="g1",
            moves=[
                _blunder_move(1, game_phase=0, tactical_pattern=1),
                _blunder_move(3, game_phase=1, tactical_pattern=2),
            ],
        )

    async def test_no_filters(
        self, analysis_repo: AnalysisRepository, game_repo: GameRepository
    ):
        await self._seed(analysis_repo, game_repo)
        results = await analysis_repo.fetch_blunders_with_tactics()
        assert len(results) == 2

    async def test_phase_filter(
        self, analysis_repo: AnalysisRepository, game_repo: GameRepository
    ):
        await self._seed(analysis_repo, game_repo)
        results = await analysis_repo.fetch_blunders_with_tactics(game_phases=[0])
        assert len(results) == 1

    async def test_tactical_pattern_filter(
        self, analysis_repo: AnalysisRepository, game_repo: GameRepository
    ):
        await self._seed(analysis_repo, game_repo)
        results = await analysis_repo.fetch_blunders_with_tactics(tactical_patterns=[1])
        assert len(results) == 1

    async def test_player_color_filter(
        self, analysis_repo: AnalysisRepository, game_repo: GameRepository
    ):
        await self._seed(analysis_repo, game_repo)
        results = await analysis_repo.fetch_blunders_with_tactics(player_colors=[0])
        assert len(results) == 2
        results = await analysis_repo.fetch_blunders_with_tactics(player_colors=[1])
        assert len(results) == 0

    async def test_game_type_filter(
        self, analysis_repo: AnalysisRepository, game_repo: GameRepository
    ):
        await self._seed(analysis_repo, game_repo)
        blitz_type = GAME_TYPE_FROM_STRING["blitz"]
        results = await analysis_repo.fetch_blunders_with_tactics(
            game_types=[blitz_type]
        )
        assert len(results) == 2
        bullet_type = GAME_TYPE_FROM_STRING["bullet"]
        results = await analysis_repo.fetch_blunders_with_tactics(
            game_types=[bullet_type]
        )
        assert len(results) == 0


class TestTacticsBackfill:
    async def test_get_game_ids_missing_tactics(
        self, analysis_repo: AnalysisRepository
    ):
        await _write_game(analysis_repo, game_id="g1", moves=[_blunder_move(1)])
        await _write_game(
            analysis_repo,
            game_id="g2",
            moves=[_blunder_move(1, tactical_pattern=1)],
        )
        ids = await analysis_repo.get_game_ids_missing_tactics()
        assert "g1" in ids
        assert "g2" not in ids

    async def test_fetch_blunders_for_tactics_backfill(
        self, analysis_repo: AnalysisRepository
    ):
        await _write_game(
            analysis_repo,
            moves=[
                _blunder_move(1),
                _make_move(2),
                _blunder_move(3, tactical_pattern=1),
            ],
        )
        blunders = await analysis_repo.fetch_blunders_for_tactics_backfill("g1")
        assert len(blunders) == 1
        assert blunders[0]["ply"] == 1

    async def test_update_move_tactics(self, analysis_repo: AnalysisRepository):
        await _write_game(analysis_repo, moves=[_blunder_move(1)])
        await analysis_repo.update_move_tactics("g1", 1, 3, "hanging piece")
        result = await analysis_repo.get_move_analysis("g1", 1)
        assert result["tactical_pattern"] == 3
        assert result["tactical_reason"] == "hanging piece"
