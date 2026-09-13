def test_hourly_stats_timezone_fallback_validation_and_cache_key(app):
    utc = app.get("/api/stats/games/by-hour")
    los_angeles = app.get("/api/stats/games/by-hour?timezone=America/Los_Angeles")
    invalid = app.get("/api/stats/games/by-hour?timezone=Not/A_Timezone")

    assert utc.status_code == 200
    assert utc.json()["timezone"] == "UTC"
    assert los_angeles.status_code == 200
    assert los_angeles.json()["timezone"] == "America/Los_Angeles"
    assert invalid.status_code == 422
