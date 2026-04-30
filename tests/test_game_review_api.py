from __future__ import annotations

from http import HTTPStatus
from fastapi.testclient import TestClient


def test_review_endpoint_game_not_found(app: TestClient) -> None:
    resp = app.get("/api/games/nonexistent/review")
    assert resp.status_code == HTTPStatus.NOT_FOUND


async def test_review_returns_game_info(
    app: TestClient,
    game_repo,
    analysis_repo,
) -> None:
    await game_repo.insert_games(
        [
            {
                "id": "review-test-001",
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

    resp = app.get("/api/games/review-test-001/review")
    assert resp.status_code == HTTPStatus.OK

    data = resp.json()
    assert data["game"]["id"] == "review-test-001"
    assert data["game"]["white"] == "testuser"
    assert data["game"]["black"] == "opponent"
    assert data["game"]["result"] == "1-0"
    assert data["game"]["source"] == "lichess"
    assert data["game"]["username"] == "testuser"
    assert data["analyzed"] is False
    assert data["moves"] == []


async def test_review_returns_analyzed_moves_with_labels(
    app: TestClient,
    game_repo,
    analysis_repo,
) -> None:
    await game_repo.insert_games(
        [
            {
                "id": "review-test-002",
                "source": "lichess",
                "username": "testuser",
                "white": "testuser",
                "black": "opponent",
                "result": "0-1",
                "date": "2025.01.15",
                "end_time_utc": "2025-01-15T12:00:00",
                "time_control": "180+0",
                "pgn_content": '[Site "https://lichess.org/xyz"]\n\n1. e4 e5 0-1\n',
            }
        ]
    )

    await analysis_repo.write_analysis(
        game_id="review-test-002",
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

    resp = app.get("/api/games/review-test-002/review")
    assert resp.status_code == HTTPStatus.OK

    data = resp.json()
    assert data["analyzed"] is True
    assert len(data["moves"]) == 2

    move1 = data["moves"][0]
    assert move1["ply"] == 1
    assert move1["san"] == "e4"
    assert move1["player"] == "white"
    assert move1["classification"] == "normal"

    move2 = data["moves"][1]
    assert move2["ply"] == 2
    assert move2["san"] == "e5"
    assert move2["player"] == "black"
    assert move2["classification"] == "blunder"
    assert move2["cp_loss"] == 280


async def test_review_includes_game_url(
    app: TestClient,
    game_repo,
) -> None:
    await game_repo.insert_games(
        [
            {
                "id": "review-test-003",
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

    resp = app.get("/api/games/review-test-003/review")
    assert resp.status_code == HTTPStatus.OK

    data = resp.json()
    assert data["game"]["game_url"] is not None
    assert "lichess.org" in data["game"]["game_url"]


def test_review_ui_route_returns_html(app: TestClient) -> None:
    resp = app.get("/game/some-game-id")
    assert resp.status_code == HTTPStatus.OK
    assert "text/html" in resp.headers["content-type"]
