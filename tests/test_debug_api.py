from __future__ import annotations

from http import HTTPStatus
from fastapi.testclient import TestClient


def test_debug_endpoint_game_not_found(app: TestClient) -> None:
    resp = app.get("/api/games/nonexistent/debug")
    assert resp.status_code == HTTPStatus.NOT_FOUND


async def test_debug_endpoint_returns_text(
    app: TestClient,
    game_repo,
    analysis_repo,
) -> None:
    await game_repo.insert_games(
        [
            {
                "id": "test-game-001",
                "source": "lichess",
                "username": "testuser",
                "white": "testuser",
                "black": "opponent",
                "result": "1-0",
                "date": "2025.01.15",
                "end_time_utc": "2025-01-15T12:00:00",
                "time_control": "300+3",
                "pgn_content": '[Site "https://lichess.org/abc123"]\n\n1. e4 e5 1-0\n',
            }
        ]
    )

    await analysis_repo.write_analysis(
        game_id="test-game-001",
        pgn_path="test.pgn",
        analyzed_at="2025-01-15T12:00:00",
        engine_path="/usr/bin/stockfish",
        depth=10,
        time_limit=1.0,
        thresholds={"inaccuracy": 50, "mistake": 100, "blunder": 200},
        moves=[
            {
                "ply": 1,
                "move_number": 1,
                "player": "white",
                "uci": "e2e4",
                "san": "e4",
                "eval_before": 20,
                "eval_after": 30,
                "delta": 10,
                "cp_loss": 0,
                "classification": 0,
            },
            {
                "ply": 2,
                "move_number": 1,
                "player": "black",
                "uci": "e7e5",
                "san": "e5",
                "eval_before": 30,
                "eval_after": -250,
                "delta": -280,
                "cp_loss": 280,
                "classification": 3,
                "best_move_uci": "d7d5",
                "best_move_san": "d5",
            },
        ],
    )

    resp = app.get("/api/games/test-game-001/debug")
    assert resp.status_code == HTTPStatus.OK
    assert resp.headers["content-type"] == "text/plain; charset=utf-8"

    text = resp.text
    assert "test-game-001" in text
    assert "lichess" in text
    assert "testuser" in text
    assert "1. e4 e5 1-0" in text
    assert "## Blunders Summary" in text
    assert "e5" in text
    assert "## Analysis (move-by-move)" in text
    assert "Currently Investigating" not in text

    resp_with_ply = app.get("/api/games/test-game-001/debug?ply=2")
    assert resp_with_ply.status_code == HTTPStatus.OK
    text_with_ply = resp_with_ply.text
    assert "## ⚠️ Currently Investigating (ply 2)" in text_with_ply
    assert "← 🔍" in text_with_ply
    assert "🔍 **Ply 2**" in text_with_ply
