from __future__ import annotations

import re
from pathlib import Path

from blunder_tutor.web.vite import ENTRY_MAP

VITE_CONFIG = Path(__file__).resolve().parent.parent / "frontend" / "vite.config.ts"


def _parse_vite_inputs(config_source: str) -> dict[str, str]:
    """Extract the ``rollupOptions.input`` map from ``vite.config.ts``.

    We don't need a full TS parser — the config is an object literal with
    a ``key: resolve(__dirname, 'path')`` shape. A regex over that is
    both adequate and resilient to formatting changes.
    """
    # Match: key (bareword or quoted) ':' resolve(__dirname, 'some/path')
    # Keys like 'game-review' appear quoted.
    pattern = re.compile(
        r"(?:'([\w\-]+)'|(\w+))\s*:\s*resolve\(\s*__dirname\s*,\s*'([^']+)'\s*\)"
    )
    return {
        (quoted or bare): path for quoted, bare, path in pattern.findall(config_source)
    }


class TestViteEntryParity:
    """Vite-asset rendering in tests runs in dev mode (no manifest), so a
    drift between ``ENTRY_MAP`` and the production ``vite.config.ts``
    input map wouldn't be caught at runtime. This test closes the gap.
    """

    def test_every_entry_map_key_is_declared_in_vite_config(self):
        inputs = _parse_vite_inputs(VITE_CONFIG.read_text())

        missing = [name for name in ENTRY_MAP if name not in inputs]
        assert missing == [], (
            f"ENTRY_MAP keys missing from vite.config.ts input map: {missing}. "
            "Add the corresponding rollupOptions.input entry, or remove the "
            "ENTRY_MAP entry if the page was retired."
        )

    def test_entry_map_sources_match_vite_inputs(self):
        inputs = _parse_vite_inputs(VITE_CONFIG.read_text())

        for name, src in ENTRY_MAP.items():
            declared = inputs.get(name)
            assert declared == src, (
                f"ENTRY_MAP[{name!r}] points at {src!r} but vite.config.ts "
                f"declares it at {declared!r}. Fix one or the other."
            )
