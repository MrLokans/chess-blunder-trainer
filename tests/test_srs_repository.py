from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta

from blunder_tutor.repositories.srs_repository import SrsRepository
from blunder_tutor.srs import CardState, SrsCard, enroll

NOW = datetime(2026, 7, 7, 12, 0, tzinfo=UTC)
NOW_ISO = NOW.isoformat()


def _card(game_id: str = "g1", ply: int = 10, **overrides: object) -> SrsCard:
    base = enroll(game_id, ply, NOW - timedelta(days=2))
    if overrides:
        return replace(base, **overrides)  # type: ignore[arg-type]
    return base


class TestCardRoundTrip:
    async def test_get_missing_returns_none(self, srs_repo: SrsRepository):
        assert await srs_repo.get_card("nope", 1) is None

    async def test_upsert_and_get(self, srs_repo: SrsRepository):
        await srs_repo.upsert_card(_card())
        card = await srs_repo.get_card("g1", 10)
        assert card is not None
        assert card.rung == 0
        assert card.state is CardState.ACTIVE
        assert card.total_failures == 1

    async def test_upsert_replaces(self, srs_repo: SrsRepository):
        await srs_repo.upsert_card(_card())
        await srs_repo.upsert_card(_card(rung=2, total_failures=3))
        card = await srs_repo.get_card("g1", 10)
        assert card.rung == 2
        assert card.total_failures == 3


class TestDueQueries:
    async def test_due_includes_overdue_excludes_future(self, srs_repo: SrsRepository):
        await srs_repo.upsert_card(_card("g1", 1))
        await srs_repo.upsert_card(
            _card("g2", 1, due_at=(NOW + timedelta(days=3)).isoformat())
        )
        assert await srs_repo.get_due_keys(NOW_ISO) == [("g1", 1)]
        assert await srs_repo.count_due(NOW_ISO) == 1

    async def test_due_at_exactly_now_is_due(self, srs_repo: SrsRepository):
        await srs_repo.upsert_card(_card("g1", 1, due_at=NOW_ISO))
        assert await srs_repo.count_due(NOW_ISO) == 1

    async def test_non_active_states_never_due(self, srs_repo: SrsRepository):
        await srs_repo.upsert_card(_card("g1", 1, state=CardState.GRADUATED))
        await srs_repo.upsert_card(_card("g2", 1, state=CardState.SUSPENDED))
        assert await srs_repo.count_due(NOW_ISO) == 0

    async def test_count_active_and_next_due(self, srs_repo: SrsRepository):
        later = (NOW + timedelta(days=3)).isoformat()
        await srs_repo.upsert_card(_card("g1", 1, due_at=NOW_ISO))
        await srs_repo.upsert_card(_card("g2", 1, due_at=later))
        await srs_repo.upsert_card(_card("g3", 1, state=CardState.SUSPENDED))
        assert await srs_repo.count_active() == 2
        assert await srs_repo.next_due_at() == NOW_ISO

    async def test_next_due_at_empty_returns_none(self, srs_repo: SrsRepository):
        assert await srs_repo.next_due_at() is None


class TestActiveKeys:
    async def test_only_graduated_cards_excluded(self, srs_repo: SrsRepository):
        await srs_repo.upsert_card(_card("g1", 1))
        await srs_repo.upsert_card(_card("g2", 1, state=CardState.GRADUATED))
        await srs_repo.upsert_card(_card("g3", 1, state=CardState.SUSPENDED))
        assert await srs_repo.active_keys() == {("g1", 1), ("g3", 1)}


class TestDeleteAll:
    async def test_delete_all_returns_count(self, srs_repo: SrsRepository):
        await srs_repo.upsert_card(_card("g1", 1))
        await srs_repo.upsert_card(_card("g2", 1))
        assert await srs_repo.delete_all() == 2
        assert await srs_repo.get_card("g1", 1) is None
