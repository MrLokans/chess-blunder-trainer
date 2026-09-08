import re
from pathlib import Path

FORBIDDEN_TOKENS = (
    "red",
    "blue",
    "yellow",
    "black",
    "white",
    "warm-gray",
    "mid-gray",
    "mid-gray-light",
    "dark-gray",
    "correct",
    "bg",
    "bg-elevated",
    "text-faint",
    "card-bg",
    "primary",
    "color-primary",
    "color-primary-hover",
    "color-success",
    "color-success-bg",
    "color-success-border",
    "color-warning",
    "color-warning-bg",
    "color-warning-border",
    "color-error",
    "color-error-bg",
    "color-error-border",
    "color-info",
    "color-info-bg",
    "color-info-border",
    "color-slate-50",
    "color-slate-100",
    "color-slate-200",
    "color-slate-300",
    "color-slate-400",
    "color-slate-500",
    "color-slate-600",
    "color-slate-700",
    "color-slate-800",
    "color-slate-900",
)
TOKEN_REFERENCE = re.compile(
    rf"(?:var\(\s*|['\"])--(?:{'|'.join(FORBIDDEN_TOKENS)})(?![-\w])"
)
SOURCE_ROOTS = (
    Path("blunder_tutor/web/static"),
    Path("frontend/src"),
    Path("templates"),
    Path("e2e"),
)
SOURCE_SUFFIXES = {".css", ".html", ".js", ".ts", ".tsx"}
EXEMPT_FILES = {
    Path("blunder_tutor/web/static/css/chessground-theme.css"),
    Path("blunder_tutor/web/static/css/tokens.css"),
}


class TestSemanticTokenBoundary:
    def test_themeable_sources_do_not_use_structural_or_deleted_tokens(self):
        violations = []
        for root in SOURCE_ROOTS:
            for path in root.rglob("*"):
                if (
                    path.suffix in SOURCE_SUFFIXES
                    and path not in EXEMPT_FILES
                    and TOKEN_REFERENCE.search(path.read_text(encoding="utf-8"))
                ):
                    violations.append(path)
        assert not violations
