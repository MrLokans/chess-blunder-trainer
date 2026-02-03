"""Tests for system API endpoints."""


def test_get_engine_status_returns_engine_info(app):
    response = app.get("/api/system/engine")
    assert response.status_code == 200

    data = response.json()
    assert data["available"] is True
    assert data["name"] == "Stockfish 17"
    assert data["path"] == "/usr/bin/stockfish"


def test_get_engine_status_includes_author(app):
    response = app.get("/api/system/engine")
    data = response.json()
    assert "author" in data
