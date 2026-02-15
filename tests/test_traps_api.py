"""Tests for traps API endpoints."""

from __future__ import annotations

from fastapi.testclient import TestClient

EXPECTED_CATALOG_KEYS = {
    "id",
    "name",
    "category",
    "rating_range",
    "victim_side",
    "mistake_ply",
    "mistake_san",
    "refutation_pgn",
    "refutation_move",
    "refutation_note",
    "recognition_tip",
    "tags",
}


class TestGetTrapCatalog:
    def test_returns_list(self, app: TestClient):
        response = app.get("/api/traps/catalog")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0

    def test_items_have_expected_keys(self, app: TestClient):
        response = app.get("/api/traps/catalog")
        data = response.json()
        for item in data:
            assert EXPECTED_CATALOG_KEYS.issubset(item.keys())

    def test_each_trap_has_id_and_name(self, app: TestClient):
        response = app.get("/api/traps/catalog")
        data = response.json()
        for item in data:
            assert item["id"]
            assert item["name"]


class TestGetTrapStats:
    def test_returns_stats_and_summary(self, app: TestClient):
        response = app.get("/api/traps/stats")
        assert response.status_code == 200
        data = response.json()
        assert "stats" in data
        assert "summary" in data
        assert isinstance(data["stats"], list)
        assert isinstance(data["summary"], dict)


class TestGetTrapDetail:
    def test_valid_trap_id(self, app: TestClient):
        response = app.get("/api/traps/scholars_mate")
        assert response.status_code == 200
        data = response.json()
        assert "trap" in data
        assert "history" in data
        assert data["trap"] is not None
        assert data["trap"]["id"] == "scholars_mate"
        assert EXPECTED_CATALOG_KEYS.issubset(data["trap"].keys())

    def test_invalid_trap_id(self, app: TestClient):
        response = app.get("/api/traps/nonexistent_trap_xyz")
        assert response.status_code == 200
        data = response.json()
        assert data["trap"] is None
        assert isinstance(data["history"], list)
