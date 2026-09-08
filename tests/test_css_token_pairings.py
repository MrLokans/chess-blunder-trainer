import re
from pathlib import Path

BRAND_BACKGROUND = re.compile(
    r"background(?:-color)?:\s*var\(--(?:warning|badge-primary|error|accent|success|info|piece-[^)]+)\)"
)
FLIPPING_TEXT = re.compile(r"color:\s*var\(--text(?:-inverse|-secondary)?\)")


def test_brand_backgrounds_do_not_use_flipping_text_tokens():
    violations = []
    for path in Path("blunder_tutor/web/static/css").glob("*.css"):
        for block in re.findall(
            r"[^{}]+\{([^{}]*)\}", path.read_text(encoding="utf-8")
        ):
            if BRAND_BACKGROUND.search(block) and FLIPPING_TEXT.search(block):
                violations.append(path)
    assert not violations
