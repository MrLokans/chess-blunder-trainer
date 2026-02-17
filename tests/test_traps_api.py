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
    "entry_san_variants",
    "trap_san_variants",
    "refutation_san",
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

    def test_move_sequences_are_lists_of_san(self, app: TestClient):
        response = app.get("/api/traps/catalog")
        data = response.json()
        for item in data:
            assert isinstance(item["entry_san_variants"], list)
            assert isinstance(item["trap_san_variants"], list)
            assert isinstance(item["refutation_san"], list)
            for variant in item["entry_san_variants"]:
                assert isinstance(variant, list)
                assert all(isinstance(m, str) for m in variant)
            for variant in item["trap_san_variants"]:
                assert isinstance(variant, list)
                assert all(isinstance(m, str) for m in variant)


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

    def test_detail_includes_move_sequences(self, app: TestClient):
        response = app.get("/api/traps/scholars_mate")
        data = response.json()
        trap = data["trap"]
        assert isinstance(trap["entry_san_variants"], list)
        assert isinstance(trap["trap_san_variants"], list)
        assert isinstance(trap["refutation_san"], list)
        assert len(trap["refutation_san"]) > 0

    def test_invalid_trap_id(self, app: TestClient):
        response = app.get("/api/traps/nonexistent_trap_xyz")
        assert response.status_code == 200
        data = response.json()
        assert data["trap"] is None
        assert isinstance(data["history"], list)
