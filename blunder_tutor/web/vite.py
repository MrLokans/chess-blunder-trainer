from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from markupsafe import Markup

ENTRY_MAP = {
    "trainer": "src/trainer/index.ts",
    "dashboard": "src/dashboard/index.ts",
    "settings": "src/settings/index.tsx",
    "management": "src/management/index.ts",
    "import": "src/import/index.ts",
    "setup": "src/setup/index.ts",
    "starred": "src/starred/index.ts",
    "game-review": "src/game-review/index.ts",
    "traps": "src/traps/index.ts",
    "heatmap": "src/heatmap/index.ts",
    "growth": "src/growth/index.ts",
}

DEFAULT_DIST_DIR = Path(__file__).resolve().parent / "static" / "dist"


@lru_cache(maxsize=1)
def _load_manifest(dist_dir: Path) -> dict:
    manifest_path = dist_dir / ".vite" / "manifest.json"
    with manifest_path.open() as f:
        return json.load(f)


def vite_asset(
    entry_name: str,
    *,
    dist_dir: Path = DEFAULT_DIST_DIR,
    dev_mode: bool = False,
    dev_origin: str = "http://localhost:5173",
) -> str:
    src_entry = ENTRY_MAP.get(entry_name)
    if src_entry is None:
        raise KeyError(
            f"Unknown Vite entry: {entry_name!r}. Known entries: {list(ENTRY_MAP)}"
        )

    if dev_mode:
        return Markup(
            f'<script type="module" src="{dev_origin}/@vite/client"></script>\n'
            f'<script type="module" src="{dev_origin}/{src_entry}"></script>'
        )

    manifest = _load_manifest(dist_dir)
    if src_entry not in manifest:
        raise KeyError(
            f"Entry {src_entry!r} not found in Vite manifest. Did you run 'npm run build'?"
        )

    asset_file = manifest[src_entry]["file"]
    tags = f'<script type="module" src="/static/dist/{asset_file}"></script>'

    css_files = manifest[src_entry].get("css", [])
    for css_file in css_files:
        tags = f'<link rel="stylesheet" href="/static/dist/{css_file}">\n' + tags

    return Markup(tags)
