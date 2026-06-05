from __future__ import annotations

import pytest

from blunder_tutor.repositories.trap_repository import TrapRepository
from tests.helpers.seeding import insert_game_index_row


@pytest.fixture
async def trap_repo(db_path):
    insert_game_index_row(
        db_path,
        game_id="game1",
        username="player1",
        white="player1",
        black="opponent1",
        result="0-1",
        date="2025-01-01",
        analyzed=1,
    )
    insert_game_index_row(
        db_path,
        game_id="game2",
        username="player1",
        white="opponent2",
        black="player1",
        result="1-0",
        date="2025-01-02",
        analyzed=1,
    )
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
