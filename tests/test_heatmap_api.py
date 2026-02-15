"""Tests for activity heatmap API endpoint."""

from blunder_tutor.repositories.puzzle_attempt_repository import PuzzleAttemptRepository


def test_get_activity_heatmap_returns_empty_when_no_data(app):
    response = app.get("/api/stats/activity-heatmap")
    assert response.status_code == 200

    data = response.json()
    assert data["daily_counts"] == {}
    assert data["max_count"] == 0
    assert data["total_days"] == 0
    assert data["total_attempts"] == 0


def test_get_activity_heatmap_accepts_days_param(app):
    response = app.get("/api/stats/activity-heatmap?days=30")
    assert response.status_code == 200

    data = response.json()
    assert "daily_counts" in data
    assert "max_count" in data


def test_get_activity_heatmap_rejects_invalid_days(app):
    response = app.get("/api/stats/activity-heatmap?days=10")
    assert response.status_code == 422

    response = app.get("/api/stats/activity-heatmap?days=500")
    assert response.status_code == 422


async def test_heatmap_reflects_puzzle_attempts(db_path, app):
    repo = PuzzleAttemptRepository(db_path)
    try:
        await repo.record_attempt("game1", 10, True, "e2e4", "e2e4")
        await repo.record_attempt("game1", 20, False, "d2d4", "e2e4")
    finally:
        await repo.close()

    response = app.get("/api/stats/activity-heatmap?days=30")
    assert response.status_code == 200
    data = response.json()
    assert data["total_attempts"] >= 2
    assert data["max_count"] >= 1
