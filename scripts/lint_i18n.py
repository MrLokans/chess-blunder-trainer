#!/usr/bin/env python3
"""i18n linter for blunder-tutor.

Four checks against ``locales/*.json`` and the codebase that consumes
them, split into two severity tiers:

  ERRORS — always fail the build (catch *active* bugs):

  1. Completeness — every locale must define every key in the union
     of all locale keysets. A locale missing a key falls back to the
     raw key string at runtime, which is exactly the bug class this
     tool exists to prevent.

  2. Used but not defined — a key referenced from code but missing
     from ``en.json``. (Once #1 passes, this implies missing
     everywhere.)

  WARNINGS — printed but exit 0 by default; pass ``--strict`` to
  promote to errors. These flag *cleanup* opportunities, not active
  bugs, and can produce false positives that need human review:

  3. English fallback — in non-English locales, a multi-word value
     byte-equal to its English counterpart is *often* an unfinished
     translation. False positives: deliberate borrowings (file
     formats like "PGN", loanwords like "puzzle" in Spanish chess
     vocabulary). Review each finding before promoting to error.

  4. Defined but not used — a locale key with no callsite anywhere
     in the scanned source. Catches dead translations that drift
     during refactors. False positives: keys constructed via
     dynamic Python patterns the bare-string scan can't see; add
     such namespaces to ``DYNAMIC_PREFIXES`` below.

Dynamic-key callsites are detected automatically:
  * Template literal:  ``t(`prefix.${var}`)``  → wildcard ``prefix.*``
  * String concat:     ``t('prefix.' + var)``  → wildcard ``prefix.*``
  * Bare string mention anywhere in source (lookup tables, ternaries:
    ``const KEY = isFoo ? 'a.b.c' : 'a.b.d'``) — any string literal
    whose content exactly matches a known locale key counts as a
    reference. The ``lowercase.dotted`` shape makes accidental
    matches against unrelated strings vanishingly unlikely.
  * Python dynamic:    ``t(some_var.key, ...)`` — not statically
    grep-able, so the namespaces involved are listed in
    ``DYNAMIC_PREFIXES`` below.

Exit code:
  0 — no errors (warnings may still be printed)
  1 — any error, or any warning when ``--strict`` is set
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

#: The reference locale. Other locales are diff'd against this one for
#: the English-fallback check. Completeness is symmetric (every locale
#: must contain every key in the union), so this only affects #2 and
#: which file we treat as the source of truth for #3.
REFERENCE_LOCALE = "en"

#: Source roots scanned for ``t('key')`` callsites. Tests count as
#: callsites — they often serve as documentation of which keys exist.
#: ``blunder_tutor`` covers both backend Python (lookup tables like
#: ``utils/explanation.py``'s ``chess.piece.*`` map) and the static
#: JS that ships under ``web/static/js`` — the ``EXCLUDED_PATH_FRAGMENTS``
#: list keeps build output (``static/dist/``, ``__pycache__``) out.
SOURCE_ROOTS: tuple[str, ...] = (
    "frontend/src",
    "frontend/tests",
    "templates",
    "blunder_tutor",
)

#: File extensions considered source. ``.html`` covers Jinja templates,
#: ``.py`` covers the backend.
SOURCE_EXTENSIONS: frozenset[str] = frozenset(
    {".ts", ".tsx", ".js", ".html", ".py"}
)

#: Path fragments that mark a directory as build output, never source.
EXCLUDED_PATH_FRAGMENTS: tuple[str, ...] = (
    "node_modules",
    "/dist/",
    "/.vite/",
    "__pycache__",
)

#: Key prefixes constructed dynamically by Python code that the
#: bare-string scan can't see (e.g. ``f"{base}.{case}"`` in
#: ``utils/explanation.py``, or ``t(explanation.blunder.key)`` where
#: ``key`` is a dataclass attribute). Any locale key starting with
#: one of these is treated as referenced.
DYNAMIC_PREFIXES: tuple[str, ...] = (
    "chess.piece.",  # piece_key + grammatical case suffix
    "explanation.best.",
    "explanation.blunder.",
)

#: Allowlist for the English-fallback warning. Keyed on ``(locale,
#: key)``; the value is a one-line justification kept inline so the
#: rationale travels with the entry. Add an entry here only when the
#: identical-to-English value is a *deliberate* borrowing (file
#: formats, brand names, project-standardized loanwords) — never as a
#: shortcut around an unfinished translation.
INTENTIONAL_BORROWINGS: dict[tuple[str, str], str] = {
    # Spanish locale uses ``puzzle`` / ``puzzles`` as the established
    # chess-training vocabulary (cf. ``dashboard.chart.puzzle_activity
    # = "Actividad de puzzles"``, ``settings.features.starred_puzzles
    # = "Puzzles favoritos"``). Translating these heatmap strings to
    # ``rompecabezas`` would diverge from the rest of the locale.
    ("es", "heatmap.tooltip"): "es puzzle borrowing (matches rest of es locale)",
    ("es", "heatmap.total"): "es puzzle borrowing (matches rest of es locale)",
    # ``PGN`` is the chess game file format — universally untranslated.
    # ``Import`` is also a valid Polish noun (cognate with English).
    ("pl", "import.title"): "PGN file format + Polish/English cognate noun",
}

# ---------------------------------------------------------------------------
# Regexes
# ---------------------------------------------------------------------------

#: ``t('foo.bar.baz')`` / ``t("foo.bar")`` — fully-static key. Anchored
#: on a word boundary so the pattern doesn't match e.g. ``somet('x')``.
_LITERAL_KEY = re.compile(r"\bt\(\s*['\"]([a-z][a-z0-9_]*(?:\.[a-z0-9_]+)+)['\"]")

#: ``t(`foo.bar.${var}`)`` — extract the static prefix before the first
#: ``${``. The regex is intentionally non-greedy so a trailing ``${``
#: terminates capture; anything inside the literal after that is
#: dynamic and contributes only its prefix as a wildcard.
_TEMPLATE_KEY_PREFIX = re.compile(
    r"\bt\(\s*`([a-z][a-z0-9_.]*?)\$\{"
)

#: ``t('foo.bar.' + var)`` / ``t("foo.bar." + var)`` — extract the
#: static prefix. Requires the prefix to end with ``.`` so we don't
#: accidentally capture something like ``t('greeting' + name)``.
_CONCAT_KEY_PREFIX = re.compile(
    r"\bt\(\s*['\"]([a-z][a-z0-9_]*(?:\.[a-z0-9_]+)*\.)['\"]\s*\+"
)

#: Bare string literal of the i18n-key shape — minimum two segments,
#: lowercase + digits + underscore, dot-separated. Matched anywhere
#: in source; a hit only counts as a reference if the matched string
#: equals a known locale key (filtered downstream). The shape is
#: distinctive enough that accidental matches against non-i18n
#: strings (URLs, log tags, etc.) are extremely rare.
_BARE_KEY = re.compile(
    r"['\"`]([a-z][a-z0-9_]*(?:\.[a-z0-9_]+)+)['\"`]"
)


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------


@dataclass
class Findings:
    # Errors (always fail).
    missing_in_locales: dict[str, list[str]] = field(default_factory=dict)
    used_not_defined: list[tuple[str, str]] = field(default_factory=list)
    # Warnings (fail only under --strict).
    english_fallback: list[tuple[str, str, str]] = field(default_factory=list)
    defined_not_used: list[str] = field(default_factory=list)

    def error_count(self) -> int:
        return (
            sum(len(v) for v in self.missing_in_locales.values())
            + len(self.used_not_defined)
        )

    def warning_count(self) -> int:
        return len(self.english_fallback) + len(self.defined_not_used)


# ---------------------------------------------------------------------------
# Locale loading
# ---------------------------------------------------------------------------


def load_locales(locales_dir: Path) -> dict[str, dict[str, str]]:
    locales: dict[str, dict[str, str]] = {}
    for path in sorted(locales_dir.glob("*.json")):
        with path.open(encoding="utf-8") as fh:
            locales[path.stem] = json.load(fh)
    if REFERENCE_LOCALE not in locales:
        raise SystemExit(
            f"[i18n-lint] Reference locale '{REFERENCE_LOCALE}' "
            f"not found in {locales_dir}"
        )
    return locales


# ---------------------------------------------------------------------------
# Source scanning
# ---------------------------------------------------------------------------


def iter_source_files(root: Path) -> Iterable[Path]:
    for src_root in SOURCE_ROOTS:
        base = root / src_root
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if path.suffix not in SOURCE_EXTENSIONS:
                continue
            posix = path.as_posix()
            if any(frag in posix for frag in EXCLUDED_PATH_FRAGMENTS):
                continue
            yield path


def scan_sources(
    root: Path,
) -> tuple[
    dict[str, list[tuple[Path, int]]],
    set[str],
    set[str],
    int,
]:
    """Return (literal callsites, bare-string mentions, dynamic prefixes, files).

    ``literal_refs`` is keyed on the key string and carries first-hit
    locations for ``t('foo.bar')`` callsites — used both for the
    "used-not-defined" check (we can point at the callsite) and for
    the "defined-not-used" check (positive evidence of use).

    ``bare_mentions`` is the set of i18n-key-shaped strings found
    anywhere in source, regardless of whether they're inside a
    ``t()`` call. The "defined-not-used" check intersects this with
    locale keys to give a lookup-table-aware notion of "used".
    """
    literal_refs: dict[str, list[tuple[Path, int]]] = {}
    bare_mentions: set[str] = set()
    dynamic_prefixes: set[str] = set(DYNAMIC_PREFIXES)
    file_count = 0
    for path in iter_source_files(root):
        file_count += 1
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for line_no, line in enumerate(text.splitlines(), start=1):
            for m in _LITERAL_KEY.finditer(line):
                literal_refs.setdefault(m.group(1), []).append((path, line_no))
            for m in _TEMPLATE_KEY_PREFIX.finditer(line):
                prefix = m.group(1)
                if prefix.endswith("."):
                    dynamic_prefixes.add(prefix)
            for m in _CONCAT_KEY_PREFIX.finditer(line):
                dynamic_prefixes.add(m.group(1))
            for m in _BARE_KEY.finditer(line):
                bare_mentions.add(m.group(1))
    return literal_refs, bare_mentions, dynamic_prefixes, file_count


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------


def check_completeness(
    locales: dict[str, dict[str, str]],
    findings: Findings,
) -> None:
    union = set().union(*(set(d.keys()) for d in locales.values()))
    for locale, data in locales.items():
        missing = sorted(union - set(data.keys()))
        if missing:
            findings.missing_in_locales[locale] = missing


def check_english_fallback(
    locales: dict[str, dict[str, str]],
    findings: Findings,
) -> None:
    en = locales[REFERENCE_LOCALE]
    for locale, data in locales.items():
        if locale == REFERENCE_LOCALE:
            continue
        for key, value in sorted(data.items()):
            ref = en.get(key)
            if ref is None or ref != value:
                continue
            # Single-word values (brand names, chess terms) often
            # legitimately stay in English. Multi-word identical
            # values are almost certainly an unfinished translation.
            if len(value.split()) < 2:
                continue
            # Explicitly-acknowledged borrowings (PGN, project's
            # established Spanish "puzzle" vocabulary, etc.).
            if (locale, key) in INTENTIONAL_BORROWINGS:
                continue
            findings.english_fallback.append((locale, key, value))


def check_used_not_defined(
    literal_refs: dict[str, list[tuple[Path, int]]],
    locales: dict[str, dict[str, str]],
    findings: Findings,
) -> None:
    en_keys = set(locales[REFERENCE_LOCALE].keys())
    for key in sorted(literal_refs):
        if key in en_keys:
            continue
        first_path, first_line = literal_refs[key][0]
        findings.used_not_defined.append(
            (key, f"{first_path.as_posix()}:{first_line}")
        )


def check_defined_not_used(
    literal_refs: dict[str, list[tuple[Path, int]]],
    bare_mentions: set[str],
    dynamic_prefixes: set[str],
    locales: dict[str, dict[str, str]],
    findings: Findings,
) -> None:
    referenced = set(literal_refs) | bare_mentions
    en_keys = set(locales[REFERENCE_LOCALE].keys())
    for key in sorted(en_keys):
        if key in referenced:
            continue
        if any(key.startswith(p) for p in dynamic_prefixes):
            continue
        findings.defined_not_used.append(key)


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------


def report(findings: Findings) -> None:
    # Errors.
    if findings.missing_in_locales:
        total = sum(len(v) for v in findings.missing_in_locales.values())
        print(
            f"\n✗ ERROR · MISSING IN LOCALES ({total} key/locale gaps):",
            file=sys.stderr,
        )
        for locale in sorted(findings.missing_in_locales):
            for key in findings.missing_in_locales[locale]:
                print(f"  {locale}: {key}", file=sys.stderr)

    if findings.used_not_defined:
        print(
            f"\n✗ ERROR · USED BUT NOT DEFINED ({len(findings.used_not_defined)} "
            f"keys referenced in code but missing from {REFERENCE_LOCALE}.json):",
            file=sys.stderr,
        )
        for key, location in findings.used_not_defined:
            print(f"  {key}  ({location})", file=sys.stderr)

    # Warnings.
    if findings.english_fallback:
        print(
            f"\n⚠ WARNING · ENGLISH FALLBACK ({len(findings.english_fallback)} "
            "multi-word values byte-equal to English — review for borrowings):",
            file=sys.stderr,
        )
        for locale, key, value in findings.english_fallback:
            print(f"  {locale}: {key} = {value!r}", file=sys.stderr)

    if findings.defined_not_used:
        print(
            f"\n⚠ WARNING · DEFINED BUT NOT USED ({len(findings.defined_not_used)} "
            "keys with no callsite — likely dead code from a refactor):",
            file=sys.stderr,
        )
        for key in findings.defined_not_used:
            print(f"  {key}", file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parent.parent,
        help="Project root (default: parent of this script)",
    )
    parser.add_argument(
        "--locales-dir",
        type=Path,
        default=None,
        help="Override locales directory (default: <root>/locales)",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat warnings as errors (English-fallback + unused-key checks).",
    )
    args = parser.parse_args(argv)

    root: Path = args.root.resolve()
    locales_dir: Path = (args.locales_dir or root / "locales").resolve()

    locales = load_locales(locales_dir)
    literal_refs, bare_mentions, dynamic_prefixes, file_count = scan_sources(root)

    print(
        f"[i18n-lint] {len(locales)} locales · "
        f"{len(locales[REFERENCE_LOCALE])} keys · "
        f"{file_count} source files scanned · "
        f"{len(dynamic_prefixes)} dynamic prefixes",
        file=sys.stderr,
    )

    findings = Findings()
    check_completeness(locales, findings)
    check_english_fallback(locales, findings)
    check_used_not_defined(literal_refs, locales, findings)
    check_defined_not_used(
        literal_refs, bare_mentions, dynamic_prefixes, locales, findings
    )

    report(findings)

    errors = findings.error_count()
    warnings = findings.warning_count()
    if errors == 0 and warnings == 0:
        print("[i18n-lint] OK", file=sys.stderr)
        return 0
    if errors == 0 and not args.strict:
        print(
            f"\n[i18n-lint] OK — {warnings} warning(s); pass --strict to fail.",
            file=sys.stderr,
        )
        return 0
    print(
        f"\n[i18n-lint] FAIL — {errors} error(s), {warnings} warning(s)"
        + ("" if errors else " (treated as errors under --strict)"),
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
