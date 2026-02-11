from __future__ import annotations

from collections.abc import AsyncGenerator
from pathlib import Path

import pytest

from blunder_tutor.repositories.starred_puzzle_repository import StarredPuzzleRepository


@pytest.fixture
async def starred_repo(db_path: Path) -> AsyncGenerator[StarredPuzzleRepository]:
    repo = StarredPuzzleRepository(db_path)
    yield repo
    await repo.close()


class TestStarredPuzzleRepository:
    async def test_star_and_is_starred(self, starred_repo: StarredPuzzleRepository):
        assert not await starred_repo.is_starred("game1", 10)
        await starred_repo.star("game1", 10)
        assert await starred_repo.is_starred("game1", 10)

    async def test_unstar(self, starred_repo: StarredPuzzleRepository):
        await starred_repo.star("game1", 10)
        assert await starred_repo.unstar("game1", 10)
        assert not await starred_repo.is_starred("game1", 10)

    async def test_unstar_nonexistent_returns_false(
        self, starred_repo: StarredPuzzleRepository
    ):
        assert not await starred_repo.unstar("game1", 10)

    async def test_star_with_note(self, starred_repo: StarredPuzzleRepository):
        await starred_repo.star("game1", 10, note="Important blunder")
        items = await starred_repo.list_starred()
        assert len(items) == 1
        assert items[0]["note"] == "Important blunder"

    async def test_star_replaces_existing(self, starred_repo: StarredPuzzleRepository):
        await starred_repo.star("game1", 10, note="first")
        await starred_repo.star("game1", 10, note="second")
        items = await starred_repo.list_starred()
        assert len(items) == 1
        assert items[0]["note"] == "second"

    async def test_list_starred_empty(self, starred_repo: StarredPuzzleRepository):
        items = await starred_repo.list_starred()
        assert items == []

    async def test_list_starred_ordering(self, starred_repo: StarredPuzzleRepository):
        await starred_repo.star("game1", 10)
        await starred_repo.star("game2", 20)
        await starred_repo.star("game3", 30)
        items = await starred_repo.list_starred()
        assert len(items) == 3
        assert items[0]["game_id"] == "game3"

    async def test_list_starred_pagination(self, starred_repo: StarredPuzzleRepository):
        for i in range(5):
            await starred_repo.star(f"game{i}", i * 10)
        items = await starred_repo.list_starred(limit=2, offset=0)
        assert len(items) == 2
        items2 = await starred_repo.list_starred(limit=2, offset=2)
        assert len(items2) == 2

    async def test_count_starred(self, starred_repo: StarredPuzzleRepository):
        assert await starred_repo.count_starred() == 0
        await starred_repo.star("game1", 10)
        await starred_repo.star("game2", 20)
        assert await starred_repo.count_starred() == 2

    async def test_delete_all(self, starred_repo: StarredPuzzleRepository):
        await starred_repo.star("game1", 10)
        await starred_repo.star("game2", 20)
        count = await starred_repo.delete_all()
        assert count == 2
        assert await starred_repo.count_starred() == 0


class TestStarredAPI:
    def test_star_puzzle(self, app):
        resp = app.put("/api/starred/game1/10", json={})
        assert resp.status_code == 200
        assert resp.json()["starred"] is True

    def test_check_starred(self, app):
        app.put("/api/starred/game1/10", json={})
        resp = app.get("/api/starred/game1/10")
        assert resp.status_code == 200
        assert resp.json()["starred"] is True

    def test_check_not_starred(self, app):
        resp = app.get("/api/starred/game1/10")
        assert resp.status_code == 200
        assert resp.json()["starred"] is False

    def test_unstar_puzzle(self, app):
        app.put("/api/starred/game1/10", json={})
        resp = app.delete("/api/starred/game1/10")
        assert resp.status_code == 200
        assert resp.json()["starred"] is False

    def test_unstar_nonexistent_returns_404(self, app):
        resp = app.delete("/api/starred/game1/10")
        assert resp.status_code == 404

    def test_list_starred_empty(self, app):
        resp = app.get("/api/starred")
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []
        assert data["total"] == 0

    def test_list_starred_with_items(self, app):
        app.put("/api/starred/game1/10", json={})
        app.put("/api/starred/game2/20", json={"note": "test note"})
        resp = app.get("/api/starred")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        assert len(data["items"]) == 2

    def test_star_with_note(self, app):
        app.put("/api/starred/game1/10", json={"note": "remember this"})
        resp = app.get("/api/starred")
        data = resp.json()
        assert data["items"][0]["note"] == "remember this"

    def test_starred_page_loads(self, app):
        resp = app.get("/starred")
        assert resp.status_code == 200


class TestStarredDemoMode:
    @pytest.fixture
    def demo_app(self, test_config):
        from unittest.mock import AsyncMock, MagicMock, patch

        import chess
        import chess.engine
        from fastapi.testclient import TestClient

        from blunder_tutor.web.app import create_app

        mock_engine = MagicMock()
        mock_engine.id = {"name": "Stockfish 17", "author": "test"}
        mock_engine.analyse = AsyncMock(
            return_value={
                "score": chess.engine.PovScore(chess.engine.Cp(50), chess.WHITE),
                "pv": [],
            }
        )
        mock_engine.quit = AsyncMock()
        rc_future = MagicMock()
        rc_future.done.return_value = False
        mock_engine.returncode = rc_future
        mock_transport = MagicMock()

        async def mock_popen_uci(path):
            return (mock_transport, mock_engine)

        test_config.demo_mode = True

        with patch("chess.engine.popen_uci", mock_popen_uci):
            fastapi_app = create_app(test_config)
            with TestClient(fastapi_app) as client:
                yield client

    def test_demo_blocks_star(self, demo_app):
        resp = demo_app.put("/api/starred/game1/10", json={})
        assert resp.status_code == 403

    def test_demo_blocks_unstar(self, demo_app):
        resp = demo_app.delete("/api/starred/game1/10")
        assert resp.status_code == 403

    def test_demo_allows_list(self, demo_app):
        resp = demo_app.get("/api/starred")
        assert resp.status_code == 200

    def test_demo_allows_check(self, demo_app):
        resp = demo_app.get("/api/starred/game1/10")
        assert resp.status_code == 200


class TestDataWipeIncludesStarred:
    async def test_delete_all_clears_starred(
        self, db_path: Path, starred_repo: StarredPuzzleRepository
    ):
        from blunder_tutor.repositories.data_management import DataManagementRepository

        await starred_repo.star("game1", 10)
        await starred_repo.star("game2", 20)
        assert await starred_repo.count_starred() == 2

        mgmt = DataManagementRepository(db_path)
        try:
            counts = await mgmt.delete_all_data()
            assert counts["starred_puzzles"] == 2
        finally:
            await mgmt.close()

        assert await starred_repo.count_starred() == 0
