from __future__ import annotations

from http import HTTPStatus

from blunder_tutor.web.api.stats import _compute_growth_windows
from tests.helpers.stats_db import insert_test_game, insert_test_move


def _make_game_data(
    blunder_count: int = 1,
    avg_cpl: float = 50.0,
    avg_blunder_cpl: float = 300.0,
    catastrophic_count: int = 0,
) -> dict:
    return {
        "game_id": "g",
        "end_time_utc": "2025-01-01",
        "blunder_count": blunder_count,
        "avg_cpl": avg_cpl,
        "avg_blunder_cpl": avg_blunder_cpl,
        "catastrophic_count": catastrophic_count,
        "total_blunders": blunder_count,
    }


class TestComputeGrowthWindows:
    def test_empty_data(self):
        assert _compute_growth_windows([], 20) == []

    def test_insufficient_games(self):
        games = [_make_game_data() for _ in range(10)]
        assert _compute_growth_windows(games, 20) == []

    def test_single_window(self):
        games = [_make_game_data(blunder_count=2, avg_cpl=60.0) for _ in range(20)]
        windows = _compute_growth_windows(games, 20)
        assert len(windows) == 1
        assert windows[0].avg_blunders_per_game == 2.0
        assert windows[0].avg_cpl == 60.0

    def test_two_windows(self):
        old_games = [_make_game_data(blunder_count=3, avg_cpl=80.0) for _ in range(5)]
        new_games = [_make_game_data(blunder_count=1, avg_cpl=40.0) for _ in range(5)]
        windows = _compute_growth_windows(old_games + new_games, 5)
        assert len(windows) == 2
        assert windows[0].avg_blunders_per_game == 3.0
        assert windows[1].avg_blunders_per_game == 1.0

    def test_clean_game_rate(self):
        games = [_make_game_data(blunder_count=0) for _ in range(3)]
        games += [_make_game_data(blunder_count=2) for _ in range(2)]
        windows = _compute_growth_windows(games, 5)
        assert windows[0].clean_game_rate == 60.0

    def test_catastrophic_rate(self):
        games = [
            _make_game_data(blunder_count=2, catastrophic_count=1) for _ in range(5)
        ]
        windows = _compute_growth_windows(games, 5)
        assert windows[0].catastrophic_rate == 50.0

    def test_blunder_rates_are_null_without_blunders(self):
        games = [
            _make_game_data(blunder_count=0, avg_blunder_cpl=0.0, catastrophic_count=0)
            for _ in range(5)
        ]
        windows = _compute_growth_windows(games, 5)
        assert windows[0].catastrophic_rate is None
        assert windows[0].avg_blunder_severity is None

    def test_partial_window_dropped_from_the_oldest_end(self):
        games = [_make_game_data(blunder_count=5) for _ in range(3)]
        games += [_make_game_data(blunder_count=1) for _ in range(20)]
        windows = _compute_growth_windows(games, 10)
        assert len(windows) == 2
        assert (windows[0].game_start, windows[-1].game_end) == (4, 23)
        assert all(w.avg_blunders_per_game == 1.0 for w in windows)


class TestGetGrowthMetricsRepository:
    async def test_empty_returns_empty(self, stats_repo):
        result = await stats_repo.get_growth_metrics()
        assert result == []

    async def test_returns_per_game_aggregates(self, stats_repo):
        await insert_test_game(
            stats_repo,
            "g1",
            "alice",
            "alice",
            "bob",
            end_time_utc="2025-01-01T10:00:00Z",
        )
        await insert_test_move(stats_repo, "g1", 1, 0, classification=0, cp_loss=10)
        await insert_test_move(stats_repo, "g1", 3, 0, classification=3, cp_loss=300)
        await insert_test_move(stats_repo, "g1", 5, 0, classification=3, cp_loss=600)

        result = await stats_repo.get_growth_metrics()
        assert len(result) == 1
        game = result[0]
        assert game["blunder_count"] == 2
        assert game["catastrophic_count"] == 1

    async def test_excludes_opponent_moves(self, stats_repo):
        await insert_test_game(
            stats_repo,
            "g1",
            "alice",
            "alice",
            "bob",
            end_time_utc="2025-01-01T10:00:00Z",
        )
        await insert_test_move(stats_repo, "g1", 1, 0, classification=3, cp_loss=300)
        await insert_test_move(stats_repo, "g1", 2, 1, classification=3, cp_loss=500)

        result = await stats_repo.get_growth_metrics()
        assert len(result) == 1
        assert result[0]["blunder_count"] == 1

    async def test_ordered_by_time(self, stats_repo):
        await insert_test_game(
            stats_repo,
            "g2",
            "alice",
            "alice",
            "bob",
            end_time_utc="2025-01-02T10:00:00Z",
        )
        await insert_test_game(
            stats_repo,
            "g1",
            "alice",
            "alice",
            "bob",
            end_time_utc="2025-01-01T10:00:00Z",
        )
        await insert_test_move(stats_repo, "g1", 1, 0, cp_loss=10)
        await insert_test_move(stats_repo, "g2", 1, 0, cp_loss=20)

        result = await stats_repo.get_growth_metrics()
        assert result[0]["game_id"] == "g1"
        assert result[1]["game_id"] == "g2"


class TestGrowthApiEndpoint:
    def test_empty_db(self, app):
        resp = app.get("/api/stats/growth")
        assert resp.status_code == HTTPStatus.OK
        data = resp.json()
        assert data["windows"] == []
        assert "trend" not in data
        assert data["total_games"] == 0

    async def test_insufficient_for_trends(self, app, stats_repo):
        for i in range(15):
            gid = f"g{i}"
            await insert_test_game(
                stats_repo,
                gid,
                "alice",
                "alice",
                "bob",
                end_time_utc=f"2025-01-{i + 1:02d}T10:00:00Z",
            )
            await insert_test_move(stats_repo, gid, 1, 0, classification=3, cp_loss=200)

        resp = app.get("/api/stats/growth")
        data = resp.json()
        assert data["total_games"] == 15
        assert data["windows"] == []

    async def test_custom_window_size(self, app, stats_repo):
        for i in range(12):
            gid = f"g{i}"
            await insert_test_game(
                stats_repo,
                gid,
                "alice",
                "alice",
                "bob",
                end_time_utc=f"2025-01-{i + 1:02d}T10:00:00Z",
            )
            await insert_test_move(stats_repo, gid, 1, 0, classification=3, cp_loss=200)

        resp = app.get("/api/stats/growth?window_size=5")
        data = resp.json()
        assert data["window_size"] == 5
        assert len(data["windows"]) == 2
        assert data["windows"][0]["game_start"] == 3
