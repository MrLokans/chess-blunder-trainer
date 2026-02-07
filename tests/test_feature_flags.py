from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from blunder_tutor.features import DEFAULTS, Feature
from blunder_tutor.repositories.settings import SettingsRepository


@pytest.fixture
async def settings_repo():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        repo = SettingsRepository(db_path=db_path)
        await repo.ensure_settings_table()
        try:
            yield repo
        finally:
            await repo.close()


async def test_defaults_all_enabled(settings_repo: SettingsRepository):
    flags = await settings_repo.get_feature_flags()
    for feature in Feature:
        assert flags[feature.value] is True


async def test_set_and_get_flags(settings_repo: SettingsRepository):
    await settings_repo.set_feature_flags(
        {"page.dashboard": False, "trainer.tactics": False}
    )
    flags = await settings_repo.get_feature_flags()
    assert flags["page.dashboard"] is False
    assert flags["trainer.tactics"] is False
    assert flags["page.management"] is True


async def test_set_ignores_invalid_keys(settings_repo: SettingsRepository):
    await settings_repo.set_feature_flags({"bogus.key": False, "page.dashboard": False})
    flags = await settings_repo.get_feature_flags()
    assert flags["page.dashboard"] is False
    assert "bogus.key" not in flags


async def test_toggle_back_on(settings_repo: SettingsRepository):
    await settings_repo.set_feature_flags({"dashboard.heatmap": False})
    flags = await settings_repo.get_feature_flags()
    assert flags["dashboard.heatmap"] is False

    await settings_repo.set_feature_flags({"dashboard.heatmap": True})
    flags = await settings_repo.get_feature_flags()
    assert flags["dashboard.heatmap"] is True


async def test_defaults_dict_covers_all_features():
    assert set(DEFAULTS.keys()) == set(Feature)
