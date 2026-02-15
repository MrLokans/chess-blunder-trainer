"""Tests for StatsRepository methods not covered by collapse_point/conversion_resilience tests."""

from __future__ import annotations

import pytest

from blunder_tutor.repositories.job_repository import JobRepository
from blunder_tutor.repositories.stats_repository import StatsRepository
from tests.helpers.stats_db import insert_test_game, insert_test_move


@pytest.fixture
async def stats_repo(db_path):
    repo = StatsRepository(db_path)
    yield repo
    await repo.close()


@pytest.fixture
async def job_repo(db_path):
    repo = JobRepository(db_path)
    yield repo
    await repo.close()


async def _seed_blunder_game(
    stats_repo,
    game_id="g1",
    username="testuser",
    white="testuser",
    black="opponent",
    *,
    result="1-0",
    time_control="300+0",
    end_time_utc="2025-01-15T10:00:00Z",
    eco_code=None,
    eco_name=None,
    blunder_ply=5,
    blunder_player=0,
    cp_loss=250,
    game_phase=None,
    tactical_pattern=None,
    difficulty=None,
):
    await insert_test_game(
        stats_repo,
        game_id,
        username,
        white,
        black,
        result=result,
        time_control=time_control,
        end_time_utc=end_time_utc,
        eco_code=eco_code,
        eco_name=eco_name,
    )
    await insert_test_move(
        stats_repo,
        game_id,
        blunder_ply,
        blunder_player,
        classification=3,
        cp_loss=cp_loss,
        game_phase=game_phase,
        tactical_pattern=tactical_pattern,
        difficulty=difficulty,
    )


class TestGetGameBreakdown:
    async def test_empty(self, stats_repo):
        result = await stats_repo.get_game_breakdown()
        assert result == []

    async def test_with_data(self, stats_repo):
        await insert_test_game(stats_repo, "g1", "alice", "alice", "bob")
        await insert_test_game(stats_repo, "g2", "alice", "alice", "carol")
        result = await stats_repo.get_game_breakdown()
        assert len(result) == 1
        assert result[0]["username"] == "alice"
        assert result[0]["total_games"] == 2

    async def test_source_filter(self, stats_repo):
        await insert_test_game(stats_repo, "g1", "alice", "alice", "bob")
        conn = await stats_repo.get_connection()
        await conn.execute(
            "UPDATE game_index_cache SET source = 'chesscom' WHERE game_id = 'g1'"
        )
        await conn.commit()
        await insert_test_game(stats_repo, "g2", "alice", "alice", "bob")
        result = await stats_repo.get_game_breakdown(source="lichess")
        assert len(result) == 1
        assert result[0]["total_games"] == 1


class TestGetBlunderBreakdown:
    async def test_empty(self, stats_repo):
        result = await stats_repo.get_blunder_breakdown()
        assert result["total_blunders"] == 0
        assert result["avg_cp_loss"] == 0.0

    async def test_with_blunders(self, stats_repo):
        await _seed_blunder_game(stats_repo, cp_loss=200)
        await _seed_blunder_game(
            stats_repo,
            game_id="g2",
            cp_loss=400,
            blunder_ply=7,
            end_time_utc="2025-01-16T10:00:00Z",
        )
        result = await stats_repo.get_blunder_breakdown()
        assert result["total_blunders"] == 2
        assert result["avg_cp_loss"] == pytest.approx(300.0)
        assert len(result["blunders_by_date"]) > 0


class TestGetAnalysisProgress:
    async def test_empty(self, stats_repo):
        result = await stats_repo.get_analysis_progress()
        assert result["total_jobs"] == 0

    async def test_with_jobs(self, stats_repo, job_repo):
        job_id = await job_repo.create_job("analysis", username="testuser")
        await job_repo.update_job_status(job_id, "completed")
        job_id2 = await job_repo.create_job("analysis", username="testuser")
        await job_repo.update_job_status(job_id2, "failed", error_message="timeout")
        result = await stats_repo.get_analysis_progress()
        assert result["total_jobs"] == 2
        assert result["completed_jobs"] == 1
        assert result["failed_jobs"] == 1


class TestGetBlundersByPhase:
    async def test_empty(self, stats_repo):
        result = await stats_repo.get_blunders_by_phase()
        assert result["total_blunders"] == 0
        assert result["by_phase"] == []

    async def test_with_phases(self, stats_repo):
        await _seed_blunder_game(stats_repo, game_id="g1", game_phase=0, cp_loss=200)
        await _seed_blunder_game(
            stats_repo,
            game_id="g2",
            game_phase=1,
            cp_loss=300,
            blunder_ply=7,
            end_time_utc="2025-01-16T10:00:00Z",
        )
        result = await stats_repo.get_blunders_by_phase()
        assert result["total_blunders"] == 2
        phases = {p["phase"]: p for p in result["by_phase"]}
        assert "opening" in phases
        assert "middlegame" in phases
        assert phases["opening"]["count"] == 1


class TestGetBlundersByColor:
    async def test_white_vs_black(self, stats_repo):
        await _seed_blunder_game(
            stats_repo,
            game_id="g1",
            white="testuser",
            black="opp",
            blunder_player=0,
            blunder_ply=5,
        )
        await _seed_blunder_game(
            stats_repo,
            game_id="g2",
            white="opp",
            black="testuser",
            blunder_player=1,
            blunder_ply=6,
            end_time_utc="2025-01-16T10:00:00Z",
        )
        result = await stats_repo.get_blunders_by_color()
        assert result["total_blunders"] == 2
        colors = {c["color"]: c for c in result["by_color"]}
        assert "white" in colors
        assert "black" in colors


class TestGetBlundersByGameType:
    async def test_different_types(self, stats_repo):
        await _seed_blunder_game(
            stats_repo,
            game_id="g1",
            time_control="60+0",
        )
        await _seed_blunder_game(
            stats_repo,
            game_id="g2",
            time_control="600+0",
            blunder_ply=7,
            end_time_utc="2025-01-16T10:00:00Z",
        )
        result = await stats_repo.get_blunders_by_game_type()
        assert result["total_blunders"] == 2
        types = {t["game_type"]: t for t in result["by_game_type"]}
        assert len(types) == 2


class TestGetRecentActivity:
    async def test_empty(self, stats_repo):
        result = await stats_repo.get_recent_activity()
        assert result == []

    async def test_with_jobs(self, stats_repo, job_repo):
        job_id = await job_repo.create_job(
            "analysis", username="testuser", source="lichess"
        )
        result = await stats_repo.get_recent_activity()
        assert len(result) == 1
        assert result[0]["job_id"] == job_id
        assert result[0]["job_type"] == "analysis"


class TestGetBlundersByEco:
    async def test_empty(self, stats_repo):
        result = await stats_repo.get_blunders_by_eco()
        assert result["total_blunders"] == 0
        assert result["by_opening"] == []

    async def test_with_eco_data(self, stats_repo):
        await _seed_blunder_game(
            stats_repo,
            game_id="g1",
            eco_code="B00",
            eco_name="Sicilian",
        )
        await _seed_blunder_game(
            stats_repo,
            game_id="g2",
            eco_code="C00",
            eco_name="French",
            blunder_ply=7,
            end_time_utc="2025-01-16T10:00:00Z",
        )
        result = await stats_repo.get_blunders_by_eco()
        assert result["total_blunders"] == 2
        openings = {o["eco_code"]: o for o in result["by_opening"]}
        assert "B00" in openings
        assert "C00" in openings


class TestGetGamesByDate:
    async def test_empty(self, stats_repo):
        result = await stats_repo.get_games_by_date()
        assert result == []

    async def test_with_data(self, stats_repo):
        await insert_test_game(
            stats_repo,
            "g1",
            "testuser",
            "testuser",
            "opp",
            end_time_utc="2025-01-15T10:00:00Z",
        )
        await insert_test_move(stats_repo, "g1", 1, 0, cp_loss=50)
        result = await stats_repo.get_games_by_date()
        assert len(result) == 1
        assert result[0]["date"] == "2025-01-15"
        assert result[0]["game_count"] == 1


class TestGetGamesByHour:
    async def test_empty(self, stats_repo):
        result = await stats_repo.get_games_by_hour()
        assert result == []

    async def test_with_data(self, stats_repo):
        await insert_test_game(
            stats_repo,
            "g1",
            "testuser",
            "testuser",
            "opp",
            end_time_utc="2025-01-15T14:30:00Z",
        )
        await insert_test_move(stats_repo, "g1", 1, 0, cp_loss=50)
        result = await stats_repo.get_games_by_hour()
        assert len(result) == 1
        assert result[0]["hour"] == 14


class TestGetBlundersByTacticalPattern:
    async def test_empty(self, stats_repo):
        result = await stats_repo.get_blunders_by_tactical_pattern()
        assert result["total_blunders"] == 0

    async def test_with_patterns(self, stats_repo):
        await _seed_blunder_game(stats_repo, game_id="g1", tactical_pattern=1)
        await _seed_blunder_game(
            stats_repo,
            game_id="g2",
            tactical_pattern=2,
            blunder_ply=7,
            end_time_utc="2025-01-16T10:00:00Z",
        )
        result = await stats_repo.get_blunders_by_tactical_pattern()
        assert result["total_blunders"] == 2
        assert len(result["by_pattern"]) == 2


class TestGetBlundersByPhaseFiltered:
    async def test_with_color_filter(self, stats_repo):
        await _seed_blunder_game(
            stats_repo,
            game_id="g1",
            game_phase=0,
            blunder_player=0,
        )
        await _seed_blunder_game(
            stats_repo,
            game_id="g2",
            game_phase=0,
            white="opp",
            black="testuser",
            blunder_player=1,
            blunder_ply=6,
            end_time_utc="2025-01-16T10:00:00Z",
        )
        result = await stats_repo.get_blunders_by_phase_filtered(player_colors=[0])
        assert result["total_blunders"] == 1


class TestGetBlundersByDifficulty:
    async def test_buckets(self, stats_repo):
        await _seed_blunder_game(stats_repo, game_id="g1", difficulty=20)
        await _seed_blunder_game(
            stats_repo,
            game_id="g2",
            difficulty=50,
            blunder_ply=7,
            end_time_utc="2025-01-16T10:00:00Z",
        )
        await _seed_blunder_game(
            stats_repo,
            game_id="g3",
            difficulty=80,
            blunder_ply=9,
            end_time_utc="2025-01-17T10:00:00Z",
        )
        result = await stats_repo.get_blunders_by_difficulty()
        assert result["total_blunders"] == 3
        buckets = {d["difficulty"]: d for d in result["by_difficulty"]}
        assert "easy" in buckets
        assert "medium" in buckets
        assert "hard" in buckets

    async def test_unscored(self, stats_repo):
        await _seed_blunder_game(stats_repo, game_id="g1", difficulty=None)
        result = await stats_repo.get_blunders_by_difficulty()
        buckets = {d["difficulty"]: d for d in result["by_difficulty"]}
        assert "unscored" in buckets
