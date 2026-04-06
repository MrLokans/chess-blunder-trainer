import json

import pytest

from blunder_tutor.web.vite import vite_asset


class TestViteAssetProduction:
    def test_resolves_entry_from_manifest(self, tmp_path):
        manifest = {
            "src/trainer/index.ts": {
                "file": "assets/trainer-abc123.js",
                "isEntry": True,
            }
        }
        manifest_path = tmp_path / ".vite" / "manifest.json"
        manifest_path.parent.mkdir(parents=True)
        manifest_path.write_text(json.dumps(manifest))
        result = vite_asset("trainer", dist_dir=tmp_path, dev_mode=False)
        assert 'src="/static/dist/assets/trainer-abc123.js"' in result
        assert 'type="module"' in result

    def test_raises_for_unknown_entry(self, tmp_path):
        manifest = {}
        manifest_path = tmp_path / ".vite" / "manifest.json"
        manifest_path.parent.mkdir(parents=True)
        manifest_path.write_text(json.dumps(manifest))
        with pytest.raises(KeyError):
            vite_asset("nonexistent", dist_dir=tmp_path, dev_mode=False)


class TestViteAssetDev:
    def test_returns_dev_server_url(self):
        result = vite_asset(
            "trainer", dev_mode=True, dev_origin="http://localhost:5173"
        )
        assert 'src="http://localhost:5173/src/trainer/index.ts"' in result
        assert 'type="module"' in result

    def test_includes_vite_client_script(self):
        result = vite_asset(
            "trainer", dev_mode=True, dev_origin="http://localhost:5173"
        )
        assert "@vite/client" in result
