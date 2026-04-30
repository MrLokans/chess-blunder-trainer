"""Tests for PGN import functionality."""

from __future__ import annotations

from http import HTTPStatus
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from blunder_tutor.web.api.import_game import _generate_game_id, _validate_and_parse_pgn
from blunder_tutor.web.config import AppConfig, DataConfig, EngineConfig
from tests.helpers.engine import make_test_client

VALID_PGN = """[Event "Test"]
[Site "Test"]
[Date "2024.01.01"]
[White "Player1"]
[Black "Player2"]
[Result "1-0"]

1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 4. Ba4 Nf6 5. O-O 1-0"""

MINIMAL_PGN = "1. e4 e5 2. Nf3 Nc6 1/2-1/2"

ILLEGAL_MOVE_PGN = """[Event "Test"]
[White "A"]
[Black "B"]
[Result "*"]

1. e4 e4 *"""

NO_MOVES_PGN = """[Event "Test"]
[White "A"]
[Black "B"]
[Result "*"]

*"""


class TestPgnValidation:
    def test_valid_pgn_parses_successfully(self):
        game, errors = _validate_and_parse_pgn(VALID_PGN)
        assert game is not None
        assert errors == []
        assert game.headers.get("White") == "Player1"

    def test_minimal_pgn_without_headers(self):
        game, errors = _validate_and_parse_pgn(MINIMAL_PGN)
        assert game is not None
        assert errors == []

    def test_empty_pgn_returns_error(self):
        game, errors = _validate_and_parse_pgn("")
        assert game is None
        assert "Invalid PGN format" in errors

    def test_whitespace_only_returns_error(self):
        game, errors = _validate_and_parse_pgn("   \n  ")
        assert game is None
        assert "Invalid PGN format" in errors

    def test_no_moves_returns_error(self):
        game, errors = _validate_and_parse_pgn(NO_MOVES_PGN)
        assert game is None
        assert any("no moves" in e.lower() for e in errors)

    def test_illegal_move_returns_error(self):
        game, errors = _validate_and_parse_pgn(ILLEGAL_MOVE_PGN)
        assert game is None
        assert any("illegal" in e.lower() for e in errors)

    def test_garbage_text_returns_error(self):
        game, errors = _validate_and_parse_pgn("this is not a pgn at all")
        assert game is None
        assert len(errors) > 0


class TestGameIdGeneration:
    def test_generates_manual_prefix(self):
        gid = _generate_game_id("1. e4 e5")
        assert gid.startswith("manual-")

    def test_different_pgns_produce_different_ids(self):
        id1 = _generate_game_id("1. e4 e5")
        id2 = _generate_game_id("1. d4 d5")
        assert id1 != id2


class TestImportApiValidation:
    def test_valid_pgn_extracts_headers(self):
        game, errors = _validate_and_parse_pgn(VALID_PGN)
        assert errors == []
        assert game is not None
        assert game.headers["White"] == "Player1"
        assert game.headers["Black"] == "Player2"
        assert game.headers["Result"] == "1-0"

    def test_move_count(self):
        game, _ = _validate_and_parse_pgn(VALID_PGN)
        assert game is not None
        moves = list(game.mainline_moves())
        assert len(moves) == 9


@pytest.fixture
def import_app(db_path: Path) -> TestClient:
    config = AppConfig(
        username="testuser",
        engine_path="/usr/bin/stockfish",
        engine=EngineConfig(path="/usr/bin/stockfish", depth=10, time_limit=1.0),
        data=DataConfig(
            db_path=db_path,
            template_dir=Path(__file__).parent.parent / "templates",
        ),
    )
    yield from make_test_client(config)


class TestImportEndpoint:
    def test_invalid_pgn_returns_errors(self, import_app: TestClient):
        resp = import_app.post("/api/import/pgn", json={"pgn": "not a pgn"})
        data = resp.json()
        assert data["success"] is False
        assert data["errors"]

    def test_empty_pgn_returns_errors(self, import_app: TestClient):
        resp = import_app.post("/api/import/pgn", json={"pgn": ""})
        data = resp.json()
        assert data["success"] is False
        assert "Invalid PGN format" in data["errors"]

    def test_no_moves_returns_errors(self, import_app: TestClient):
        resp = import_app.post("/api/import/pgn", json={"pgn": NO_MOVES_PGN})
        data = resp.json()
        assert data["success"] is False

    def test_valid_pgn_returns_job_id(self, import_app: TestClient):
        resp = import_app.post("/api/import/pgn", json={"pgn": VALID_PGN})
        data = resp.json()
        assert data["success"] is True
        assert data["job_id"]
        assert data["game_id"]
        assert data["game_id"].startswith("manual-")

    def test_job_status_is_queryable(self, import_app: TestClient):
        resp = import_app.post("/api/import/pgn", json={"pgn": VALID_PGN})
        job_id = resp.json()["job_id"]

        status_resp = import_app.get(f"/api/import/status/{job_id}")
        assert status_resp.status_code == HTTPStatus.OK
        status = status_resp.json()
        assert status["job_type"] == "import_pgn"
        assert status["status"] in ("pending", "running", "completed", "failed")

    def test_demo_mode_blocks_import(self, db_path: Path):
        config = AppConfig(
            username="testuser",
            engine_path="/usr/bin/stockfish",
            engine=EngineConfig(path="/usr/bin/stockfish", depth=10, time_limit=1.0),
            data=DataConfig(
                db_path=db_path,
                template_dir=Path(__file__).parent.parent / "templates",
            ),
            demo_mode=True,
        )
        for client in make_test_client(config):
            resp = client.post("/api/import/pgn", json={"pgn": VALID_PGN})
            assert resp.status_code == HTTPStatus.FORBIDDEN
