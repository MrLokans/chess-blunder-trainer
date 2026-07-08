from __future__ import annotations

import sqlite3
from contextlib import closing
from datetime import timedelta
from http import HTTPStatus
from pathlib import Path

from blunder_tutor.srs import enroll
from blunder_tutor.utils.time import utcnow
from tests.helpers.seeding import insert_game_index_row

_PGN = '[White "alice"]\n[Black "bob"]\n\n1. e4 e5 2. Nf3 Nc6 *'


def _seed_blunder(db_path: Path) -> tuple[str, int]:
    insert_game_index_row(db_path, game_id="g1", pgn_content=_PGN, analyzed=1)
    with closing(sqlite3.connect(str(db_path))) as conn:
        conn.execute(
            """
            INSERT INTO analysis_moves
                (game_id, ply, move_number, player, uci, san, eval_before,
                 eval_after, delta, cp_loss, classification, game_phase,
                 tactical_pattern, difficulty)
            VALUES ('g1', 3, 2, 0, 'g1f3', 'Nf3', 50, -250, -300, 300, 3, 1,
                    NULL, NULL)
            """
        )
        conn.commit()
    return ("g1", 3)


class TestSrsStatus:
    def test_empty_queue_reports_zero(self, app):
        resp = app.get("/api/srs/status")
        assert resp.status_code == HTTPStatus.OK
        assert resp.json() == {"due": 0, "active": 0, "next_due_at": None}

    async def test_due_card_counted(self, app, srs_repo, db_path):
        game_id, ply = _seed_blunder(db_path)
        await srs_repo.upsert_card(enroll(game_id, ply, utcnow() - timedelta(days=2)))
        body = app.get("/api/srs/status").json()
        assert body["due"] == 1
        assert body["active"] == 1
        assert body["next_due_at"] is not None


class TestSrsNext:
    def test_empty_queue_returns_404(self, app):
        assert app.get("/api/srs/next").status_code == HTTPStatus.NOT_FOUND

    async def test_serves_due_puzzle_with_remaining(self, app, srs_repo, db_path):
        game_id, ply = _seed_blunder(db_path)
        await srs_repo.upsert_card(enroll(game_id, ply, utcnow() - timedelta(days=2)))
        resp = app.get("/api/srs/next")
        assert resp.status_code == HTTPStatus.OK
        body = resp.json()
        assert body["game_id"] == game_id
        assert body["ply"] == ply
        assert body["srs"] == {"remaining": 1}
