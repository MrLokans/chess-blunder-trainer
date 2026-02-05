"""Tests for activity heatmap API endpoint."""


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
    # Too small
    response = app.get("/api/stats/activity-heatmap?days=10")
    assert response.status_code == 422

    # Too large
    response = app.get("/api/stats/activity-heatmap?days=500")
    assert response.status_code == 422
