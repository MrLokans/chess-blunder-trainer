from __future__ import annotations

from http import HTTPStatus

from fastapi.testclient import TestClient

from blunder_tutor.repositories.srs_repository import SrsRepository


class TestSubmitTrustsOnlyStoredPuzzle:
    def test_best_move_comes_from_db(self, submit_app: TestClient):
        resp = submit_app.post(
            "/api/submit", json={"move": "e2e4", "game_id": "g1", "ply": 1}
        )
        assert resp.status_code == HTTPStatus.OK
        body = resp.json()
        assert body["is_best"] is True
        assert body["best_uci"] == "e2e4"
        assert body["user_eval"] == 30

    def test_client_supplied_best_move_is_ignored(self, submit_app: TestClient):
        resp = submit_app.post(
            "/api/submit",
            json={
                "move": "g2g4",
                "game_id": "g1",
                "ply": 1,
                "best_move_uci": "g2g4",
                "best_move_eval": 999,
            },
        )
        assert resp.status_code == HTTPStatus.OK
        assert resp.json()["is_best"] is False
        assert resp.json()["is_blunder"] is True

    async def test_illegal_move_rejected_without_recording(
        self, submit_app: TestClient, srs_repo: SrsRepository
    ):
        # e1g1 renders as "O-O" via board.san() even though castling is illegal here.
        resp = submit_app.post(
            "/api/submit", json={"move": "e1g1", "game_id": "g1", "ply": 1}
        )
        assert resp.status_code == HTTPStatus.BAD_REQUEST
        # A recorded failed attempt would have enrolled an SRS card.
        assert await srs_repo.get_card("g1", 1) is None

    async def test_unknown_puzzle_is_404_and_not_enrolled(
        self, submit_app: TestClient, srs_repo: SrsRepository
    ):
        resp = submit_app.post(
            "/api/submit", json={"move": "e2e4", "game_id": "nope", "ply": 7}
        )
        assert resp.status_code == HTTPStatus.NOT_FOUND
        assert await srs_repo.get_card("nope", 7) is None

    def test_null_move_rejected(self, submit_app: TestClient):
        resp = submit_app.post(
            "/api/submit", json={"move": "0000", "game_id": "g1", "ply": 1}
        )
        assert resp.status_code == HTTPStatus.BAD_REQUEST

    def test_other_legal_move_is_engine_evaluated(self, submit_app: TestClient):
        resp = submit_app.post(
            "/api/submit", json={"move": "d2d4", "game_id": "g1", "ply": 1}
        )
        assert resp.status_code == HTTPStatus.OK
        body = resp.json()
        assert body["is_best"] is False
        assert body["is_blunder"] is False
        assert body["user_san"] == "d4"
        assert body["best_line"] == ["e4", "e5"]


class TestSubmitChess960:
    def test_chess960_castling_matches_stored_best(self, submit_app: TestClient):
        resp = submit_app.post(
            "/api/submit", json={"move": "f1h1", "game_id": "g960", "ply": 5}
        )
        assert resp.status_code == HTTPStatus.OK
        body = resp.json()
        assert body["is_best"] is True
        assert body["user_san"] == "O-O"
        assert body["user_uci"] == "f1h1"
