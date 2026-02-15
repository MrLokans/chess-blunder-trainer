from __future__ import annotations

import aiosqlite
import pytest

from blunder_tutor.repositories.trap_repository import TrapRepository


async def _create_test_db(db_path):
    async with aiosqlite.connect(str(db_path)) as conn:
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS trap_matches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                game_id TEXT NOT NULL,
                trap_id TEXT NOT NULL,
                match_type TEXT NOT NULL,
                victim_side TEXT NOT NULL,
                user_was_victim INTEGER NOT NULL,
                mistake_ply INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(game_id, trap_id)
            )
            """
        )
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS game_index_cache (
                game_id TEXT PRIMARY KEY,
                source TEXT,
                username TEXT,
                white TEXT,
                black TEXT,
                result TEXT,
                date TEXT,
                end_time_utc TEXT,
                time_control TEXT,
                pgn_content TEXT,
                analyzed INTEGER DEFAULT 0,
                indexed_at TEXT
            )
            """
        )
        await conn.execute(
            """
            INSERT INTO game_index_cache (game_id, source, username, white, black, result, date, analyzed)
            VALUES ('game1', 'lichess', 'player1', 'player1', 'opponent1', '0-1', '2025-01-01', 1)
            """
        )
        await conn.execute(
            """
            INSERT INTO game_index_cache (game_id, source, username, white, black, result, date, analyzed)
            VALUES ('game2', 'lichess', 'player1', 'opponent2', 'player1', '1-0', '2025-01-02', 1)
            """
        )
        await conn.commit()


@pytest.fixture
async def trap_repo(tmp_path):
    db_path = tmp_path / "test.db"
    await _create_test_db(db_path)
    repo = TrapRepository(db_path=db_path)
    try:
        yield repo
    finally:
        await repo.close()


class TestTrapRepository:
    async def test_save_and_get_stats(self, trap_repo):
        await trap_repo.save_trap_match(
            game_id="game1",
            trap_id="scholars_mate",
            match_type="sprung",
            victim_side="black",
            user_was_victim=True,
            mistake_ply=6,
        )

        stats = await trap_repo.get_trap_stats()
        assert len(stats) == 1
        assert stats[0]["trap_id"] == "scholars_mate"
        assert stats[0]["sprung"] == 1

    async def test_get_trap_summary(self, trap_repo):
        await trap_repo.save_trap_match(
            game_id="game1",
            trap_id="scholars_mate",
            match_type="sprung",
            victim_side="black",
            user_was_victim=True,
            mistake_ply=6,
        )
        await trap_repo.save_trap_match(
            game_id="game2",
            trap_id="fried_liver",
            match_type="entered",
            victim_side="black",
            user_was_victim=True,
            mistake_ply=None,
        )

        summary = await trap_repo.get_trap_summary()
        assert summary["games_with_traps"] == 2
        assert summary["total_sprung"] == 1
        assert summary["total_entered"] == 1

    async def test_get_trap_history(self, trap_repo):
        await trap_repo.save_trap_match(
            game_id="game1",
            trap_id="scholars_mate",
            match_type="sprung",
            victim_side="black",
            user_was_victim=True,
            mistake_ply=6,
        )

        history = await trap_repo.get_trap_history("scholars_mate")
        assert len(history) == 1
        assert history[0]["game_id"] == "game1"
        assert history[0]["match_type"] == "sprung"
        assert history[0]["white"] == "player1"

    async def test_upsert_on_conflict(self, trap_repo):
        await trap_repo.save_trap_match(
            game_id="game1",
            trap_id="scholars_mate",
            match_type="entered",
            victim_side="black",
            user_was_victim=True,
            mistake_ply=None,
        )
        await trap_repo.save_trap_match(
            game_id="game1",
            trap_id="scholars_mate",
            match_type="sprung",
            victim_side="black",
            user_was_victim=True,
            mistake_ply=6,
        )

        stats = await trap_repo.get_trap_stats()
        assert len(stats) == 1
        assert stats[0]["sprung"] == 1

    async def test_delete_all(self, trap_repo):
        await trap_repo.save_trap_match(
            game_id="game1",
            trap_id="scholars_mate",
            match_type="sprung",
            victim_side="black",
            user_was_victim=True,
            mistake_ply=6,
        )

        count = await trap_repo.delete_all()
        assert count == 1

        stats = await trap_repo.get_trap_stats()
        assert len(stats) == 0

    async def test_get_analyzed_game_ids_without_trap_data(self, trap_repo):
        ids_before = await trap_repo.get_analyzed_game_ids_without_trap_data()
        assert "game1" in ids_before

        await trap_repo.save_trap_match(
            game_id="game1",
            trap_id="scholars_mate",
            match_type="sprung",
            victim_side="black",
            user_was_victim=True,
            mistake_ply=6,
        )

        ids_after = await trap_repo.get_analyzed_game_ids_without_trap_data()
        assert "game1" not in ids_after
