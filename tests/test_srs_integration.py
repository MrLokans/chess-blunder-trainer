from __future__ import annotations

from datetime import timedelta
from http import HTTPStatus
from pathlib import Path

from blunder_tutor.background.jobs.delete_all_data import TABLE_ORDER
from blunder_tutor.repositories.data_management import DataManagementRepository
from blunder_tutor.repositories.srs_repository import SrsRepository
from blunder_tutor.srs import enroll
from blunder_tutor.utils.time import utcnow

START_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"


def _submit_payload(move: str) -> dict[str, object]:
    return {
        "move": move,
        "fen": START_FEN,
        "game_id": "g1",
        "ply": 1,
        "blunder_uci": "g2g4",
        "blunder_san": "g4",
        "best_move_uci": "e2e4",
        "best_move_san": "e4",
        "best_line": [],
        "player_color": "white",
        "eval_after": -300,
        "best_move_eval": 30,
    }


class TestSubmitSrsHook:
    async def test_failed_submit_enrolls_card(self, app, srs_repo: SrsRepository):
        resp = app.post("/api/submit", json=_submit_payload("g2g4"))
        assert resp.status_code == HTTPStatus.OK
        assert resp.json()["srs_suspended"] is False
        card = await srs_repo.get_card("g1", 1)
        assert card is not None
        assert card.rung == 0

    async def test_correct_first_try_not_enrolled(self, app, srs_repo: SrsRepository):
        app.post("/api/submit", json=_submit_payload("e2e4"))
        assert await srs_repo.get_card("g1", 1) is None

    async def test_correct_submit_on_active_card_climbs(
        self, app, srs_repo: SrsRepository
    ):
        await srs_repo.upsert_card(enroll("g1", 1, utcnow() - timedelta(days=2)))
        app.post("/api/submit", json=_submit_payload("e2e4"))
        card = await srs_repo.get_card("g1", 1)
        assert card.rung == 1


class TestDataWipeIncludesSrs:
    async def test_delete_all_clears_srs_cards(
        self, db_path: Path, srs_repo: SrsRepository
    ):
        await srs_repo.upsert_card(enroll("g1", 1, utcnow()))
        mgmt = DataManagementRepository(db_path)
        try:
            counts = await mgmt.delete_all_data()
            assert counts["srs_cards"] == 1
        finally:
            await mgmt.close()
        assert await srs_repo.get_card("g1", 1) is None

    def test_delete_all_data_job_covers_srs_cards(self):
        assert "srs_cards" in TABLE_ORDER
