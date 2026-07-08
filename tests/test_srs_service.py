from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

from blunder_tutor.repositories.srs_repository import SrsRepository
from blunder_tutor.services.srs_service import SrsService
from blunder_tutor.srs import LEECH_FAILURE_THRESHOLD, CardState, enroll

NOW = datetime(2026, 7, 7, 12, 0, tzinfo=UTC)


@pytest.fixture
def srs_service(srs_repo: SrsRepository) -> SrsService:
    return SrsService(srs_repo=srs_repo)


class TestOnAttempt:
    async def test_fail_without_card_enrolls(self, srs_service, srs_repo):
        await srs_service.on_attempt("g1", 10, was_correct=False)
        card = await srs_repo.get_card("g1", 10)
        assert card is not None
        assert card.rung == 0

    async def test_pass_without_card_does_nothing(self, srs_service, srs_repo):
        await srs_service.on_attempt("g1", 10, was_correct=True)
        assert await srs_repo.get_card("g1", 10) is None

    async def test_pass_on_active_card_climbs(self, srs_service, srs_repo):
        await srs_repo.upsert_card(enroll("g1", 10, NOW - timedelta(days=2)))
        await srs_service.on_attempt("g1", 10, was_correct=True)
        assert (await srs_repo.get_card("g1", 10)).rung == 1

    async def test_fail_on_active_card_resets(self, srs_service, srs_repo):
        card = replace(enroll("g1", 10, NOW - timedelta(days=9)), rung=2)
        await srs_repo.upsert_card(card)
        await srs_service.on_attempt("g1", 10, was_correct=False)
        updated = await srs_repo.get_card("g1", 10)
        assert updated.rung == 0
        assert updated.total_failures == 2

    async def test_fail_on_graduated_card_re_enrolls_fresh(self, srs_service, srs_repo):
        card = replace(
            enroll("g1", 10, NOW - timedelta(days=100)),
            state=CardState.GRADUATED,
            total_failures=5,
        )
        await srs_repo.upsert_card(card)
        await srs_service.on_attempt("g1", 10, was_correct=False)
        updated = await srs_repo.get_card("g1", 10)
        assert updated.state is CardState.ACTIVE
        assert updated.total_failures == 1

    async def test_suspended_card_untouched(self, srs_service, srs_repo):
        card = replace(enroll("g1", 10, NOW), state=CardState.SUSPENDED)
        await srs_repo.upsert_card(card)
        await srs_service.on_attempt("g1", 10, was_correct=True)
        assert (await srs_repo.get_card("g1", 10)).state is CardState.SUSPENDED

    async def test_returns_true_only_on_new_suspension(self, srs_service, srs_repo):
        card = replace(
            enroll("g1", 10, NOW - timedelta(days=2)),
            total_failures=LEECH_FAILURE_THRESHOLD - 1,
        )
        await srs_repo.upsert_card(card)
        assert await srs_service.on_attempt("g1", 10, was_correct=False) is True
        assert await srs_service.on_attempt("g1", 10, was_correct=False) is False


class TestPopDue:
    async def test_empty_queue_raises(self, srs_service):
        with pytest.raises(ValueError, match="No reviews due"):
            await srs_service.pop_due()

    async def test_returns_due_key_and_remaining(self, srs_service, srs_repo):
        await srs_repo.upsert_card(enroll("g1", 10, NOW - timedelta(days=2)))
        await srs_repo.upsert_card(enroll("g2", 20, NOW - timedelta(days=2)))
        game_id, ply, remaining = await srs_service.pop_due()
        assert (game_id, ply) in {("g1", 10), ("g2", 20)}
        assert remaining == 2


class TestStatus:
    async def test_status_shape(self, srs_service, srs_repo):
        await srs_repo.upsert_card(enroll("g1", 10, NOW - timedelta(days=2)))
        status = await srs_service.status()
        assert status["due"] == 1
        assert status["active"] == 1
        assert status["next_due_at"] is not None

    async def test_status_empty(self, srs_service):
        assert await srs_service.status() == {
            "due": 0,
            "active": 0,
            "next_due_at": None,
        }
